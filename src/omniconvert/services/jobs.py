"""Background conversion job execution (Qt-friendly worker)."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from omniconvert.core.errors import AppError, CancelledError
from omniconvert.core.formats import FormatId
from omniconvert.core.job import ConversionJob, JobStatus
from omniconvert.core.output import (
    default_output_name,
    discard_incomplete_output,
    ensure_not_overwrite_source,
    unique_path,
)
from omniconvert.core.registry import ConversionRegistry

log = logging.getLogger("omniconvert.jobs")


class ConversionWorker(QObject):
    progress = Signal(str, object, str)  # job_id, fraction|None, message
    finished_ok = Signal(str, str, str)  # job_id, output_path, message
    finished_err = Signal(str, str)  # job_id, user_message
    finished_cancel = Signal(str)

    def __init__(
        self,
        registry: ConversionRegistry,
        job: ConversionJob,
        source_format: FormatId,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.registry = registry
        self.job = job
        self.source_format = source_format
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def _is_cancelled(self) -> bool:
        return self._cancel.is_set()

    @Slot()
    def run(self) -> None:
        job = self.job
        job.status = JobStatus.RUNNING
        destination: Path | None = None
        try:
            if job.operation_id:
                op = self.registry.get_operation(job.operation_id)
            else:
                op = self.registry.resolve_for_target(
                    self.source_format, FormatId(job.target_format)
                )
                job.operation_id = op.operation_id

            out_name = job.output_name or default_output_name(
                job.source_path, op.target_format
            )
            destination = unique_path(job.output_dir, out_name)
            ensure_not_overwrite_source(job.source_path, destination)

            def on_progress(fraction: float | None, message: str) -> None:
                self.progress.emit(job.job_id, fraction, message)

            result = self.registry.convert(
                operation_id=op.operation_id,
                source=job.source_path,
                destination=destination,
                settings=job.settings,
                progress=on_progress,
                is_cancelled=self._is_cancelled,
            )
            if self._is_cancelled():
                discard_incomplete_output(destination)
                discard_incomplete_output(result.output_path)
                job.status = JobStatus.CANCELLED
                self.finished_cancel.emit(job.job_id)
                return

            job.status = JobStatus.SUCCEEDED
            job.result_path = result.output_path
            self.finished_ok.emit(job.job_id, str(result.output_path), result.message)
        except CancelledError:
            discard_incomplete_output(destination)
            job.status = JobStatus.CANCELLED
            self.finished_cancel.emit(job.job_id)
        except AppError as exc:
            discard_incomplete_output(destination)
            # Avoid logging full exception strings that may embed paths/content.
            log.warning("Conversion failed: %s", exc.user_message)
            job.status = JobStatus.FAILED
            job.error_message = exc.user_message
            self.finished_err.emit(job.job_id, exc.user_message)
        except Exception:  # noqa: BLE001 — last-resort UI safety
            discard_incomplete_output(destination)
            log.exception("Unexpected conversion error")
            job.status = JobStatus.FAILED
            job.error_message = "An unexpected error occurred during conversion."
            self.finished_err.emit(job.job_id, job.error_message)


class JobManager(QObject):
    """Runs at most one conversion job at a time (v1)."""

    job_progress = Signal(str, object, str)
    job_succeeded = Signal(str, str, str)
    job_failed = Signal(str, str)
    job_cancelled = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, registry: ConversionRegistry, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.registry = registry
        self._thread: QThread | None = None
        self._worker: ConversionWorker | None = None
        self._active_id: str | None = None

    @property
    def is_busy(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def start(
        self,
        *,
        source_path: Path,
        source_format: FormatId,
        target_format: str,
        output_dir: Path,
        output_name: str | None = None,
        settings: dict[str, Any] | None = None,
        operation_id: str | None = None,
    ) -> ConversionJob:
        if self.is_busy:
            raise RuntimeError("A conversion is already running.")

        job = ConversionJob(
            source_path=Path(source_path),
            target_format=target_format,
            output_dir=Path(output_dir),
            output_name=output_name,
            settings=settings or {},
            operation_id=operation_id,
        )
        thread = QThread(self)
        worker = ConversionWorker(self.registry, job, source_format)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self.job_progress)
        worker.finished_ok.connect(self._on_ok)
        worker.finished_err.connect(self._on_err)
        worker.finished_cancel.connect(self._on_cancel)
        worker.finished_ok.connect(thread.quit)
        worker.finished_err.connect(thread.quit)
        worker.finished_cancel.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._clear_busy)

        self._thread = thread
        self._worker = worker
        self._active_id = job.job_id
        self.busy_changed.emit(True)
        thread.start()
        return job

    def cancel(self) -> None:
        if self._worker:
            self._worker.request_cancel()

    def shutdown(self, timeout_ms: int = 5000) -> None:
        """Cancel cooperatively and wait; avoid QThread.terminate when possible.

        Subprocess helpers kill LO/FFmpeg process groups on their own timeouts.
        Forced thread terminate is a last resort and may leave inconsistent
        interpreter state — only used if the worker ignores cancel.
        """
        self.cancel()
        thread = self._thread
        if thread is not None and thread.isRunning():
            thread.quit()
            # Give converters time to notice cancel / finish AtomicWriter cleanup.
            wait_ms = max(timeout_ms, 15_000)
            if not thread.wait(wait_ms):
                log.warning(
                    "Conversion thread did not stop after cancel (%sms); "
                    "forcing terminate as last resort.",
                    wait_ms,
                )
                thread.terminate()
                thread.wait(2000)
        self._thread = None
        self._worker = None
        self._active_id = None

    def _on_ok(self, job_id: str, path: str, message: str) -> None:
        self.job_succeeded.emit(job_id, path, message)

    def _on_err(self, job_id: str, message: str) -> None:
        self.job_failed.emit(job_id, message)

    def _on_cancel(self, job_id: str) -> None:
        self.job_cancelled.emit(job_id)

    def _clear_busy(self) -> None:
        self._thread = None
        self._worker = None
        self._active_id = None
        self.busy_changed.emit(False)
