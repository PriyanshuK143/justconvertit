"""One-time optional engine install via the OS package manager.

Invokes apt (Linux) or winget (Windows) with user consent. Never downloads
binaries into the justconvertit tree and never imports network client libraries.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass

from omniconvert.platform.subprocess_util import run_capture
from omniconvert.services.dependencies import DependencyService, get_dependency_service

log = logging.getLogger("omniconvert.engine_setup")

# Generous: apt/winget may download large packages.
_INSTALL_TIMEOUT_SECONDS = 1800

# Windows winget package IDs (stable public catalog).
_WINGET_LIBREOFFICE = "TheDocumentFoundation.LibreOffice"
_WINGET_FFMPEG = "Gyan.FFmpeg"


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
    """True when we should show the first-run optional-tools prompt."""
    if engines_setup_done:
        return False
    svc = deps or get_dependency_service()
    return not (svc.libreoffice.available and svc.ffmpeg.available)


def linux_install_command() -> list[str]:
    """Preferred elevated apt install argv (pkexec when available)."""
    apt = shutil.which("apt-get") or "apt-get"
    pkgs = ["libreoffice", "ffmpeg"]
    pkexec = shutil.which("pkexec")
    if pkexec:
        return [pkexec, apt, "install", "-y", *pkgs]
    return [apt, "install", "-y", *pkgs]


def linux_manual_hint() -> str:
    return "sudo apt-get install -y libreoffice ffmpeg"


def windows_winget_commands() -> list[list[str]]:
    """One winget install command per package."""
    winget = shutil.which("winget") or "winget"
    common = [
        "install",
        "-e",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    return [
        [winget, *common, "--id", _WINGET_LIBREOFFICE],
        [winget, *common, "--id", _WINGET_FFMPEG],
    ]


def windows_manual_hint() -> str:
    return (
        f"winget install -e --id {_WINGET_LIBREOFFICE}\n"
        f"winget install -e --id {_WINGET_FFMPEG}"
    )


def install_recommended_engines() -> EngineSetupResult:
    """Run the platform package manager to install LibreOffice + FFmpeg."""
    if sys.platform.startswith("linux"):
        return _install_linux()
    if sys.platform.startswith("win"):
        return _install_windows()
    return EngineSetupResult(
        ok=False,
        message="Automatic install is only supported on Ubuntu/Linux and Windows.",
        command_hint=(
            "Install LibreOffice and FFmpeg with your system package manager, "
            "then use Settings → Re-check tools."
        ),
    )


def _install_linux() -> EngineSetupResult:
    hint = linux_manual_hint()
    if not shutil.which("apt-get") and not shutil.which("apt"):
        return EngineSetupResult(
            ok=False,
            message="Could not find apt-get on this system.",
            command_hint=hint,
        )
    cmd = linux_install_command()
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
        # No pkexec / cancelled auth — give the manual command.
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
    return _result_after_refresh(hint)


def _install_windows() -> EngineSetupResult:
    hint = windows_manual_hint()
    if not shutil.which("winget"):
        return EngineSetupResult(
            ok=False,
            message="winget was not found. Install LibreOffice and FFmpeg manually, then Re-check tools.",
            command_hint=hint,
        )
    details: list[str] = []
    for cmd in windows_winget_commands():
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
            # Continue to next package; report overall status after refresh.
            log.warning("winget failed (%s): %s", cmd[-1], err[:200])

    get_dependency_service().refresh(probe_versions=True)
    result = _result_after_refresh(hint)
    if not result.ok and details:
        return EngineSetupResult(
            ok=False,
            message=result.message,
            detail="\n".join(details)[:800],
            command_hint=hint,
        )
    return result


def _result_after_refresh(hint: str) -> EngineSetupResult:
    """Confirm binaries exist and respond to --version / -version before success."""
    svc = get_dependency_service()
    lo = svc.libreoffice.available
    ff = svc.ffmpeg.available
    lo_ver = svc.libreoffice.version
    ff_ver = svc.ffmpeg.version

    # Path present but version probe failed (e.g. broken Snap confinement).
    if lo and not lo_ver:
        return EngineSetupResult(
            ok=False,
            message=(
                "LibreOffice was found but did not report a version. "
                "It may be broken (common with Snap). Prefer: sudo apt-get install libreoffice"
            ),
            command_hint=hint,
        )
    if ff and not ff_ver:
        return EngineSetupResult(
            ok=False,
            message=(
                "FFmpeg was found but did not report a version. "
                "Try reinstalling via your package manager, then Re-check tools."
            ),
            command_hint=hint,
        )

    if lo and ff:
        return EngineSetupResult(
            ok=True,
            message=(
                "LibreOffice and FFmpeg are ready.\n"
                f"LibreOffice: {lo_ver}\n"
                f"FFmpeg: {ff_ver}"
            ),
        )
    parts: list[str] = []
    if lo:
        parts.append(f"LibreOffice found ({lo_ver})")
    else:
        parts.append("LibreOffice still missing")
    if ff:
        parts.append(f"FFmpeg found ({ff_ver})")
    else:
        parts.append("FFmpeg still missing")
    return EngineSetupResult(
        ok=False,
        message="Install finished, but some tools are still missing: "
        + "; ".join(parts)
        + ". You can retry from Settings.",
        command_hint=hint,
    )
