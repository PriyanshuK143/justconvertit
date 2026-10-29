from __future__ import annotations

from pathlib import Path

from omniconvert.services.dependencies import DependencyService, reset_dependency_service_for_tests


def test_missing_configured_path_falls_back(tmp_path: Path) -> None:
    reset_dependency_service_for_tests()
    svc = DependencyService(
        libreoffice_path=str(tmp_path / "missing-soffice"),
        ffmpeg_path=str(tmp_path / "missing-ffmpeg"),
    )
    # May or may not find system installs; configured missing must not crash.
    assert svc.libreoffice.key == "libreoffice"
    assert svc.ffmpeg.key == "ffmpeg"
    text = svc.summary_text()
    assert "LibreOffice" in text
    assert "FFmpeg" in text


def test_configured_ffmpeg_path_used(tmp_path: Path) -> None:
    reset_dependency_service_for_tests()
    fake = tmp_path / "ffmpeg.exe"
    fake.write_text("#!/bin/sh\necho ffmpeg version 0.0 test\n", encoding="utf-8")
    fake.chmod(0o755)
    svc = DependencyService(ffmpeg_path=str(fake), probe_versions=False)
    assert svc.ffmpeg.available
    assert svc.ffmpeg.path == fake
    assert svc.ffmpeg.version is None


def test_startup_probe_skips_version_by_default() -> None:
    reset_dependency_service_for_tests()
    svc = DependencyService(probe_versions=False)
    # Path may exist (Snap LO) but version must not be fetched on the fast path.
    if svc.libreoffice.available:
        assert svc.libreoffice.version is None


def test_linux_libreoffice_prefers_apt_over_snap(monkeypatch, tmp_path: Path) -> None:
    reset_dependency_service_for_tests()
    apt = tmp_path / "usr" / "bin" / "soffice"
    snap = tmp_path / "snap" / "bin" / "libreoffice"
    apt.parent.mkdir(parents=True)
    snap.parent.mkdir(parents=True)
    apt.write_text("#!/bin/sh\n", encoding="utf-8")
    snap.write_text("#!/bin/sh\n", encoding="utf-8")
    apt.chmod(0o755)
    snap.chmod(0o755)

    monkeypatch.setattr(
        "omniconvert.services.dependencies.DependencyService._linux_libreoffice_candidates",
        staticmethod(lambda: [apt, snap]),
    )
    monkeypatch.setattr(
        "omniconvert.services.dependencies.which",
        lambda _name: str(snap),
    )
    monkeypatch.setattr(
        "omniconvert.services.dependencies.sys.platform",
        "linux",
    )
    svc = DependencyService(probe_versions=False)
    assert svc.libreoffice.available
    assert svc.libreoffice.path == apt

