"""Safe subprocess helpers — list args, timeouts, no shell=True."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
from typing import Sequence

log = logging.getLogger("omniconvert.subprocess")


def _windows_no_window_flags() -> int:
    if sys.platform.startswith("win"):
        # CREATE_NO_WINDOW — avoid flashing a console for GUI-triggered tools.
        return 0x08000000
    return 0


def _kill_process_tree(proc: subprocess.Popen[str]) -> None:
    """Terminate a timed-out child; prefer process group on POSIX."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform.startswith("win"):
            proc.kill()
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                proc.kill()
    except OSError:
        log.debug("Could not kill subprocess pid=%s", proc.pid, exc_info=True)


def run_capture(
    cmd: Sequence[str],
    *,
    timeout: float,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a process with argv list (never shell), capture text output.

    On timeout the child (and its process group on POSIX) is killed so LibreOffice
    / FFmpeg do not keep running after justconvertit gives up.
    """
    kwargs: dict = {
        "args": list(cmd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "env": env,
    }
    flags = _windows_no_window_flags()
    if flags:
        kwargs["creationflags"] = flags
    # New session/process group so we can kill LO/ffmpeg descendants on timeout.
    if not sys.platform.startswith("win"):
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(**kwargs)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill_process_tree(proc)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        raise subprocess.TimeoutExpired(
            cmd=exc.cmd,
            timeout=exc.timeout,
            output=stdout,
            stderr=stderr,
        ) from None

    return subprocess.CompletedProcess(
        args=list(cmd),
        returncode=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout or "",
        stderr=stderr or "",
    )
