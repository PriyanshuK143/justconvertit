"""Local-only detection of optional conversion engines (LibreOffice, FFmpeg).

Never downloads binaries. Respects user-configured paths (including spaces)
and common Windows install locations, then falls back to PATH.

Startup must stay fast: Snap LibreOffice ``--version`` can take several seconds,
so version probing is opt-in (Settings refresh), not done on every launch.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from omniconvert.platform.reveal import which
from omniconvert.platform.subprocess_util import run_capture

log = logging.getLogger("omniconvert.deps")


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    key: str
    label: str
    available: bool
    path: Path | None
    version: str | None
    hint: str


_SERVICE: "DependencyService | None" = None


def get_dependency_service() -> "DependencyService":
    global _SERVICE
    if _SERVICE is None:
        # Cheap path-only probe — never block UI startup on --version.
        _SERVICE = DependencyService(probe_versions=False)
    return _SERVICE


def reset_dependency_service_for_tests() -> None:
    global _SERVICE
    _SERVICE = None


class DependencyService:
    """Startup + settings refresh probe for optional local tools."""

    def __init__(
        self,
        *,
        libreoffice_path: str = "",
        ffmpeg_path: str = "",
        probe_versions: bool = False,
    ) -> None:
        self._libreoffice_configured = (libreoffice_path or "").strip()
        self._ffmpeg_configured = (ffmpeg_path or "").strip()
        self._libreoffice: DependencyStatus | None = None
        self._ffmpeg: DependencyStatus | None = None
        self.refresh(probe_versions=probe_versions)

    def configure(
        self,
        *,
        libreoffice_path: str = "",
        ffmpeg_path: str = "",
        probe_versions: bool = False,
    ) -> None:
        self._libreoffice_configured = (libreoffice_path or "").strip()
        self._ffmpeg_configured = (ffmpeg_path or "").strip()
        self.refresh(probe_versions=probe_versions)

    def refresh(self, *, probe_versions: bool = False) -> None:
        self._libreoffice = self._probe_libreoffice(probe_versions=probe_versions)
        self._ffmpeg = self._probe_ffmpeg(probe_versions=probe_versions)
        log.info(
            "Optional engines — LibreOffice: %s; FFmpeg: %s",
            "yes" if self._libreoffice.available else "no",
            "yes" if self._ffmpeg.available else "no",
        )

    @property
    def libreoffice(self) -> DependencyStatus:
        assert self._libreoffice is not None
        return self._libreoffice

    @property
    def ffmpeg(self) -> DependencyStatus:
        assert self._ffmpeg is not None
        return self._ffmpeg

    def libreoffice_binary(self) -> str | None:
        st = self.libreoffice
        return str(st.path) if st.available and st.path else None

    def ffmpeg_binary(self) -> str | None:
        st = self.ffmpeg
        return str(st.path) if st.available and st.path else None

    def summary_text(self) -> str:
        lines = [
            self._line(self.libreoffice),
            self._line(self.ffmpeg),
        ]
        return "\n".join(lines)

    @staticmethod
    def _line(st: DependencyStatus) -> str:
        if st.available and st.path:
            ver = f" ({st.version})" if st.version else ""
            return f"{st.label}: found — {st.path}{ver}"
        return f"{st.label}: not found. {st.hint}"

    def _probe_libreoffice(self, *, probe_versions: bool) -> DependencyStatus:
        if sys.platform.startswith("linux"):
            hint = (
                "Install with: sudo apt install libreoffice "
                "(or set a custom path in Settings). Enables high-fidelity "
                "Office ↔ PDF and PDF → DOCX."
            )
        else:
            hint = (
                "Install LibreOffice from https://www.libreoffice.org/download/ "
                "or set a custom path in Settings. Required for high-fidelity "
                "Office ↔ PDF and PDF → DOCX."
            )
        path = self._resolve_executable(
            configured=self._libreoffice_configured,
            names=("soffice", "libreoffice", "soffice.exe", "libreoffice.exe"),
            windows_candidates=self._windows_libreoffice_candidates(),
            linux_candidates=self._linux_libreoffice_candidates(),
        )
        if path is None:
            return DependencyStatus(
                key="libreoffice",
                label="LibreOffice",
                available=False,
                path=None,
                version=None,
                hint=hint,
            )
        version = None
        if probe_versions:
            # Snap LibreOffice can take multiple seconds — only when user asks.
            version = self._version_from([str(path), "--version"], timeout=4)
        return DependencyStatus(
            key="libreoffice",
            label="LibreOffice",
            available=True,
            path=path,
            version=version,
            hint=hint,
        )

    def _probe_ffmpeg(self, *, probe_versions: bool) -> DependencyStatus:
        if sys.platform.startswith("linux"):
            hint = (
                "Install with: sudo apt install ffmpeg "
                "(or set a custom path in Settings). Enables WAV↔MP3 and "
                "video audio extract."
            )
        else:
            hint = (
                "Install FFmpeg (e.g. winget install FFmpeg) or set a custom path "
                "in Settings. Required for WAV↔MP3 and video audio extract."
            )
        path = self._resolve_executable(
            configured=self._ffmpeg_configured,
            names=("ffmpeg", "ffmpeg.exe"),
            windows_candidates=self._windows_ffmpeg_candidates(),
            linux_candidates=self._linux_ffmpeg_candidates(),
        )
        if path is None:
            return DependencyStatus(
                key="ffmpeg",
                label="FFmpeg",
                available=False,
                path=None,
                version=None,
                hint=hint,
            )
        version = None
        if probe_versions:
            version = self._version_from([str(path), "-version"], timeout=3)
        return DependencyStatus(
            key="ffmpeg",
            label="FFmpeg",
            available=True,
            path=path,
            version=version,
            hint=hint,
        )

    def _resolve_executable(
        self,
        *,
        configured: str,
        names: tuple[str, ...],
        windows_candidates: list[Path],
        linux_candidates: list[Path] | None = None,
    ) -> Path | None:
        if configured:
            p = Path(configured).expanduser()
            if p.is_file():
                return p
            log.warning("Configured executable not found: %s", configured)

        if sys.platform.startswith("win"):
            for cand in windows_candidates:
                if cand.is_file():
                    return cand

        # Prefer apt/deb paths over Snap — Snap LibreOffice cold-start is slow.
        if sys.platform.startswith("linux") and linux_candidates:
            for cand in linux_candidates:
                if cand.is_file():
                    return cand

        for name in names:
            found = which(name)
            if found:
                return Path(found)
        return None

    @staticmethod
    def _linux_libreoffice_candidates() -> list[Path]:
        if not sys.platform.startswith("linux"):
            return []
        return [
            Path("/usr/bin/soffice"),
            Path("/usr/lib/libreoffice/program/soffice"),
            Path("/usr/bin/libreoffice"),
            # Snap last — works, but first launch is often multi-second.
            Path("/snap/bin/libreoffice"),
            Path("/snap/bin/soffice"),
        ]

    @staticmethod
    def _linux_ffmpeg_candidates() -> list[Path]:
        if not sys.platform.startswith("linux"):
            return []
        return [
            Path("/usr/bin/ffmpeg"),
            Path("/snap/bin/ffmpeg"),
        ]

    @staticmethod
    def _windows_libreoffice_candidates() -> list[Path]:
        if not sys.platform.startswith("win"):
            return []
        roots: list[Path] = []
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            raw = os.environ.get(env)
            if raw:
                roots.append(Path(raw))
        out: list[Path] = []
        for root in roots:
            out.append(root / "LibreOffice" / "program" / "soffice.exe")
            lo = root / "LibreOffice"
            if lo.is_dir():
                for child in sorted(lo.glob("*/program/soffice.exe")):
                    out.append(child)
        return out

    @staticmethod
    def _windows_ffmpeg_candidates() -> list[Path]:
        if not sys.platform.startswith("win"):
            return []
        roots: list[Path] = []
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            raw = os.environ.get(env)
            if raw:
                roots.append(Path(raw))
        out: list[Path] = []
        for root in roots:
            out.append(root / "ffmpeg" / "bin" / "ffmpeg.exe")
            out.append(root / "FFmpeg" / "bin" / "ffmpeg.exe")
        return out

    @staticmethod
    def _version_from(cmd: list[str], *, timeout: float = 4) -> str | None:
        try:
            proc = run_capture(cmd, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            return None
        text = (proc.stdout or proc.stderr or "").strip().splitlines()
        if not text:
            return None
        line = text[0][:120]
        # Snap confinement noise is not a version string.
        if "snap-confine" in line.lower() or "refusing to continue" in line.lower():
            return None
        return line
