# PyInstaller runtime hook — must run before app code.
# Windowed builds leave sys.stdout / sys.stderr as None on Windows.
import os
import sys

def _ensure(stream_name: str) -> None:
    stream = getattr(sys, stream_name, None)
    if stream is None:
        setattr(
            sys,
            stream_name,
            open(os.devnull, "w", encoding="utf-8", errors="replace"),  # noqa: SIM115
        )

_ensure("stdout")
_ensure("stderr")
