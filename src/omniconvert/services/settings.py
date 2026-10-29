"""Per-user application settings (local JSON only)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from omniconvert.platform.paths import user_config_dir


@dataclass
class AppSettings:
    default_output_dir: str = ""
    jpeg_quality: int = 90
    transparency_background: str = "#FFFFFF"
    overwrite_policy: str = "suffix"  # always suffix in v1 — never silent overwrite
    theme: str = "system"  # system | light | dark
    libreoffice_path: str = ""
    ffmpeg_path: str = ""
    # True after first-run Install/Skip — do not auto-prompt again.
    engines_setup_done: bool = False
    recent_history: list[dict[str, Any]] = field(default_factory=list)
    max_history: int = 30

    def resolved_output_dir(self, fallback: Path) -> Path:
        if self.default_output_dir:
            p = Path(self.default_output_dir)
            if p.is_dir() or not p.exists():
                return p
        return fallback


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (user_config_dir() / "settings.json")

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return AppSettings()
            known = {f.name for f in AppSettings.__dataclass_fields__.values()}  # type: ignore[attr-defined]
            filtered = {k: v for k, v in data.items() if k in known}
            # Migrate older "dark" default that was actually the light stylesheet name.
            if filtered.get("theme") == "dark" and "libreoffice_path" not in data:
                # Keep explicit dark if user already had dark key alone — treat as system
                # only when migrating from pre-theme-options builds is hard; leave as-is.
                pass
            return AppSettings(**filtered)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        payload = asdict(settings)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

    def add_history(
        self,
        settings: AppSettings,
        *,
        source_name: str,
        target_format: str,
        output_path: str,
        status: str,
    ) -> AppSettings:
        entry = {
            "source_name": source_name,
            "target_format": target_format,
            "output_path": output_path,
            "status": status,
        }
        history = [entry, *settings.recent_history]
        settings.recent_history = history[: settings.max_history]
        self.save(settings)
        return settings
