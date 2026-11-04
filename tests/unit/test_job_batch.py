"""JobManager sequential batch queue."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from omniconvert.core.formats import FormatId
from omniconvert.core.registry import ConversionRegistry
from omniconvert.services.jobs import JobManager


@pytest.fixture
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_batch_converts_sequentially(
    qapp, registry: ConversionRegistry, sample_png: Path, tmp_path: Path
) -> None:
    _ = qapp
    mgr = JobManager(registry)
    src2 = tmp_path / "b.png"
    src2.write_bytes(sample_png.read_bytes())
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    done: list[str] = []
    failed: list[str] = []
    batch_msgs: list[tuple[int, int]] = []

    mgr.job_succeeded.connect(lambda _jid, path, _msg: done.append(path))
    mgr.job_failed.connect(lambda _jid, msg: failed.append(msg))
    mgr.batch_progress.connect(lambda d, t, _m: batch_msgs.append((d, t)))

    specs = [
        {
            "source_path": sample_png,
            "source_format": FormatId.PNG,
            "target_format": FormatId.JPEG.value,
            "output_dir": out_dir,
            "output_name": "a.jpg",
            "settings": {"jpeg_quality": 70},
            "operation_id": "image.png_to_jpeg",
        },
        {
            "source_path": src2,
            "source_format": FormatId.PNG,
            "target_format": FormatId.JPEG.value,
            "output_dir": out_dir,
            "output_name": "b.jpg",
            "settings": {"jpeg_quality": 70},
            "operation_id": "image.png_to_jpeg",
        },
    ]
    mgr.start_batch(specs)

    # Pump the event loop until idle (both workers finished).
    for _ in range(200):
        QCoreApplication.processEvents()
        if not mgr.is_busy and len(done) + len(failed) >= 2:
            break
        import time

        time.sleep(0.05)

    assert not failed, failed
    assert len(done) == 2
    assert (out_dir / "a.jpg").exists()
    assert (out_dir / "b.jpg").exists()
    assert any(t == 2 for _, t in batch_msgs)
