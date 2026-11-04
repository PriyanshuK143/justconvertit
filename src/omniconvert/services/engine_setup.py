"""Optional engine install via the OS package manager (user consent only).

Invokes apt (Linux) or winget (Windows). Never downloads binaries into the
justconvertit tree and never imports network client libraries.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass

from omniconvert.platform.subprocess_util import run_capture
from omniconvert.services.dependencies import DependencyService, get_dependency_service

log = logging.getLogger("omniconvert.engine_setup")

# Generous: apt/winget may download large packages.
_INSTALL_TIMEOUT_SECONDS = 1800

# Windows winget package IDs (stable public catalog).
_WINGET_LIBREOFFICE = "TheDocumentFoundation.LibreOffice"
_WINGET_FFMPEG = "Gyan.FFmpeg"

_VALID_PACKAGES = frozenset({"ffmpeg", "libreoffice"})


@dataclass(frozen=True, slots=True)
class EngineSetupResult:
    ok: bool
    message: str
    detail: str = ""
    command_hint: str = ""


def needs_engine_setup(
    deps: DependencyService | None = None,
    *,
    engines_setup_done: bool,
) -> bool:
    """True when we should show the first-run optional-tools prompt.

    Windows: never nag at startup — install FFmpeg/LibreOffice only when a
    conversion needs them (or from Settings). Startup popups feel wrong for a
    portable desktop app.
    """
    if engines_setup_done:
        return False
    if sys.platform.startswith("win"):
        return False
    svc = deps or get_dependency_service()
    return not (svc.libreoffice.available and svc.ffmpeg.available)


def _normalize_packages(packages: Iterable[str] | None) -> frozenset[str]:
    if packages is None:
        return frozenset({"ffmpeg", "libreoffice"})
    out = frozenset(p.strip().lower() for p in packages if p and p.strip())
    unknown = out - _VALID_PACKAGES
    if unknown:
        raise ValueError(f"Unknown engine package(s): {sorted(unknown)}")
    if not out:
        raise ValueError("At least one engine package is required.")
    return out


def linux_install_command(packages: Iterable[str] | None = None) -> list[str]:
    """Preferred elevated apt install argv (pkexec when available)."""
    pkgs = sorted(_normalize_packages(packages))
    apt = shutil.which("apt-get") or "apt-get"
    pkexec = shutil.which("pkexec")
    if pkexec:
        return [pkexec, apt, "install", "-y", *pkgs]
    return [apt, "install", "-y", *pkgs]


def linux_manual_hint(packages: Iterable[str] | None = None) -> str:
    pkgs = " ".join(sorted(_normalize_packages(packages)))
    return f"sudo apt-get install -y {pkgs}"


def windows_winget_commands(packages: Iterable[str] | None = None) -> list[list[str]]:
    """One winget install command per selected package."""
    wanted = _normalize_packages(packages)
    winget = shutil.which("winget") or "winget"
    common = [
        "install",
        "-e",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    cmds: list[list[str]] = []
    if "libreoffice" in wanted:
        cmds.append([winget, *common, "--id", _WINGET_LIBREOFFICE])
    if "ffmpeg" in wanted:
        cmds.append([winget, *common, "--id", _WINGET_FFMPEG])
    return cmds


def windows_manual_hint(packages: Iterable[str] | None = None) -> str:
    wanted = _normalize_packages(packages)
    lines: list[str] = []
    if "libreoffice" in wanted:
        lines.append(f"winget install -e --id {_WINGET_LIBREOFFICE}")
    if "ffmpeg" in wanted:
        lines.append(f"winget install -e --id {_WINGET_FFMPEG}")
    return "\n".join(lines)


def install_recommended_engines() -> EngineSetupResult:
    """Install both LibreOffice and FFmpeg (Settings bulk action)."""
    return install_engines(("ffmpeg", "libreoffice"))


def install_engines(packages: Iterable[str]) -> EngineSetupResult:
    """Install selected engines via apt (Linux) or winget (Windows)."""
    wanted = _normalize_packages(packages)
    if sys.platform.startswith("linux"):
        return _install_linux(wanted)
    if sys.platform.startswith("win"):
        return _install_windows(wanted)
    return EngineSetupResult(
        ok=False,
        message="Automatic install is only supported on Ubuntu/Linux and Windows.",
        command_hint=(
            "Install LibreOffice and/or FFmpeg with your system package manager, "
            "then use Settings → Re-check tools."
        ),
    )


def _install_linux(wanted: frozenset[str]) -> EngineSetupResult:
    hint = linux_manual_hint(wanted)
    if not shutil.which("apt-get") and not shutil.which("apt"):
        return EngineSetupResult(
            ok=False,
            message="Could not find apt-get on this system.",
            command_hint=hint,
        )
    cmd = linux_install_command(wanted)
    log.info("Installing optional engines via: %s", " ".join(cmd))
    try:
        proc = run_capture(cmd, timeout=_INSTALL_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return EngineSetupResult(
            ok=False,
            message="Package install timed out.",
            command_hint=hint,
        )
    except OSError as exc:
        return EngineSetupResult(
            ok=False,
            message="Could not start the package installer.",
            detail=str(exc),
            command_hint=hint,
        )

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:800]
        if not shutil.which("pkexec") or "auth" in err.lower() or proc.returncode in {
            126,
            127,
        }:
            return EngineSetupResult(
                ok=False,
                message="Install did not finish. Run this in a terminal (needs admin):",
                detail=err,
                command_hint=hint,
            )
        return EngineSetupResult(
            ok=False,
            message="Install did not finish — you can retry from Settings.",
            detail=err,
            command_hint=hint,
        )

    get_dependency_service().refresh(probe_versions=True)
    return _result_after_refresh(hint, wanted)


def _install_windows(wanted: frozenset[str]) -> EngineSetupResult:
    hint = windows_manual_hint(wanted)
    if not shutil.which("winget"):
        return EngineSetupResult(
            ok=False,
            message=(
                "winget was not found. Install the App Installer from Microsoft Store, "
                "then retry — or install FFmpeg/LibreOffice manually."
            ),
            command_hint=hint,
        )
    details: list[str] = []
    for cmd in windows_winget_commands(wanted):
        log.info("Installing via winget: %s", " ".join(cmd))
        try:
            proc = run_capture(cmd, timeout=_INSTALL_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return EngineSetupResult(
                ok=False,
                message="winget install timed out.",
                command_hint=hint,
            )
        except OSError as exc:
            return EngineSetupResult(
                ok=False,
                message="Could not start winget.",
                detail=str(exc),
                command_hint=hint,
            )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()[:800]
            details.append(err)
            log.warning("winget failed (%s): %s", cmd[-1], err[:200])

    get_dependency_service().refresh(probe_versions=True)
    result = _result_after_refresh(hint, wanted)
    if not result.ok and details:
        return EngineSetupResult(
            ok=False,
            message=result.message,
            detail="\n".join(details)[:800],
            command_hint=hint,
        )
    return result


def _result_after_refresh(hint: str, wanted: frozenset[str]) -> EngineSetupResult:
    """Confirm requested binaries exist after install."""
    svc = get_dependency_service()
    lo = svc.libreoffice.available
    ff = svc.ffmpeg.available
    lo_ver = svc.libreoffice.version
    ff_ver = svc.ffmpeg.version

    if "libreoffice" in wanted and lo and not lo_ver:
        return EngineSetupResult(
            ok=False,
            message=(
                "LibreOffice was found but did not report a version. "
                "It may be broken (common with Snap). Prefer: sudo apt-get install libreoffice"
            ),
            command_hint=hint,
        )
    if "ffmpeg" in wanted and ff and not ff_ver:
        return EngineSetupResult(
            ok=False,
            message=(
                "FFmpeg was found but did not report a version. "
                "Try reinstalling via your package manager, then Re-check tools."
            ),
            command_hint=hint,
        )

    missing: list[str] = []
    ready: list[str] = []
    if "libreoffice" in wanted:
        if lo and lo_ver:
            ready.append(f"LibreOffice ({lo_ver})")
        else:
            missing.append("LibreOffice")
    if "ffmpeg" in wanted:
        if ff and ff_ver:
            ready.append(f"FFmpeg ({ff_ver})")
        else:
            missing.append("FFmpeg")

    if not missing:
        return EngineSetupResult(
            ok=True,
            message="Ready:\n" + "\n".join(ready),
        )
    parts = ready + [f"{name} still missing" for name in missing]
    return EngineSetupResult(
        ok=False,
        message="Install finished, but some tools are still missing: "
        + "; ".join(parts)
        + ". You can retry from Settings.",
        command_hint=hint,
    )
