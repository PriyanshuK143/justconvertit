"""First-run optional engine setup (apt/winget helpers — no real installs)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from omniconvert.services.dependencies import DependencyStatus
from omniconvert.services.engine_setup import (
    linux_install_command,
    linux_manual_hint,
    needs_engine_setup,
    windows_manual_hint,
    windows_winget_commands,
)


def _deps(*, lo: bool, ff: bool) -> MagicMock:
    svc = MagicMock()
    svc.libreoffice = DependencyStatus(
        key="libreoffice",
        label="LibreOffice",
        available=lo,
        path=Path("/usr/bin/soffice") if lo else None,
        version=None,
        hint="",
    )
    svc.ffmpeg = DependencyStatus(
        key="ffmpeg",
        label="FFmpeg",
        available=ff,
        path=Path("/usr/bin/ffmpeg") if ff else None,
        version=None,
        hint="",
    )
    return svc


def test_needs_engine_setup_false_when_flag_set() -> None:
    assert (
        needs_engine_setup(_deps(lo=False, ff=False), engines_setup_done=True) is False
    )


def test_needs_engine_setup_false_when_both_present() -> None:
    assert (
        needs_engine_setup(_deps(lo=True, ff=True), engines_setup_done=False) is False
    )


def test_needs_engine_setup_true_when_missing() -> None:
    assert needs_engine_setup(_deps(lo=True, ff=False), engines_setup_done=False) is True
    assert needs_engine_setup(_deps(lo=False, ff=True), engines_setup_done=False) is True
    assert needs_engine_setup(_deps(lo=False, ff=False), engines_setup_done=False) is True


def test_linux_install_command_uses_apt_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "omniconvert.services.engine_setup.shutil.which",
        lambda name: "/usr/bin/pkexec" if name == "pkexec" else "/usr/bin/apt-get",
    )
    cmd = linux_install_command()
    assert cmd[0] == "/usr/bin/pkexec"
    assert "apt-get" in cmd[1]
    assert cmd[2:4] == ["install", "-y"]
    assert "libreoffice" in cmd
    assert "ffmpeg" in cmd


def test_linux_manual_hint() -> None:
    assert "sudo apt-get install" in linux_manual_hint()
    assert "libreoffice" in linux_manual_hint()
    assert "ffmpeg" in linux_manual_hint()


def test_windows_winget_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "omniconvert.services.engine_setup.shutil.which",
        lambda name: "C:\\winget.exe" if name == "winget" else None,
    )
    cmds = windows_winget_commands()
    assert len(cmds) == 2
    flat = " ".join(" ".join(c) for c in cmds)
    assert "TheDocumentFoundation.LibreOffice" in flat
    assert "Gyan.FFmpeg" in flat
    assert "--accept-package-agreements" in flat


def test_windows_manual_hint() -> None:
    hint = windows_manual_hint()
    assert "TheDocumentFoundation.LibreOffice" in hint
    assert "Gyan.FFmpeg" in hint


def test_engines_setup_done_persists(tmp_path: Path) -> None:
    from omniconvert.services.settings import AppSettings, SettingsStore

    store = SettingsStore(tmp_path / "settings.json")
    s = AppSettings(engines_setup_done=True)
    store.save(s)
    loaded = store.load()
    assert loaded.engines_setup_done is True
