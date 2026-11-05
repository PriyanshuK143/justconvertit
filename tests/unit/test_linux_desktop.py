from __future__ import annotations

from pathlib import Path

from omniconvert.platform import linux_desktop as ld


def test_copy_icons_and_desktop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setattr(ld.sys, "platform", "linux")
    monkeypatch.setattr(ld.sys, "frozen", False, raising=False)
    monkeypatch.setattr(ld.sys, "executable", "/tmp/venv/bin/python")

    ld.ensure_linux_desktop_identity()

    desktop = tmp_path / "share" / "applications" / "justconvertit.desktop"
    assert desktop.is_file()
    text = desktop.read_text(encoding="utf-8")
    assert "Icon=justconvertit" in text
    assert "StartupWMClass=justconvertit" in text
    assert "-m omniconvert" in text

    icon = tmp_path / "share" / "icons" / "hicolor" / "256x256" / "apps" / "justconvertit.png"
    assert icon.is_file()
    assert icon.stat().st_size > 100


def test_skip_on_non_linux(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setattr(ld.sys, "platform", "win32")
    ld.ensure_linux_desktop_identity()
    assert not (tmp_path / "share" / "applications").exists()
