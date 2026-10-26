"""Configuration loader and schema validator for Ekco Parse."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


DEFAULT_CONFIG: Dict[str, Any] = {
    "character": {
        "name": "Ekco",
        "server": "green",
        "class": "Shadowknight",
    },
    "log_tailer": {
        "log_dir": "/home/ekco/Games/Project1999/Logs",
        "filename_pattern": "eqlog_{character}_{server}.txt",
        "poll_interval_sec": 0.1,
        "start_at_end": True,
        "fallback_simulator": False,
    },
    "display": {
        "theme": "antfarm_dark",
        "borderless_mode": True,
        "fps": 20,
        "tick_interval_sec": 0.25,
    },
    "combat": {
        "encounter_timeout_sec": 60.0,
        "history_limit": 50,
        "dps_window_sec": 1.0,
    },
    "map": {
        "default_zone": "East Commonlands",
        "auto_switch_zone": True,
        "max_breadcrumbs": 60,
        "grid_width": 58,
        "grid_height": 24,
    },
    "triggers": [],
}


class Config:
    """Manages application configuration, reading from YAML with fallbacks."""

    def __init__(self, config_dict: Dict[str, Any], config_path: Optional[Path] = None):
        self.raw = config_dict
        self.config_path = config_path

        # Character
        char = config_dict.get("character", {})
        self.character_name: str = char.get("name", "Ekco")
        self.server: str = char.get("server", "green")
        self.character_class: str = char.get("class", "Shadowknight")

        # Log Tailer
        tailer = config_dict.get("log_tailer", {})
        self.log_dir: Path = Path(tailer.get("log_dir", "/home/ekco/Games/Project1999/Logs")).expanduser()
        self.filename_pattern: str = tailer.get("filename_pattern", "eqlog_{character}_{server}.txt")
        self.poll_interval_sec: float = float(tailer.get("poll_interval_sec", 0.1))
        self.start_at_end: bool = bool(tailer.get("start_at_end", True))
        self.fallback_simulator: bool = bool(tailer.get("fallback_simulator", False))

        # Display
        display = config_dict.get("display", {})
        self.theme: str = display.get("theme", "antfarm_dark")
        self.borderless_mode: bool = bool(display.get("borderless_mode", True))
        self.fps: int = int(display.get("fps", 20))
        self.tick_interval_sec: float = float(display.get("tick_interval_sec", 0.25))

        # Combat
        combat = config_dict.get("combat", {})
        self.encounter_timeout_sec: float = float(combat.get("encounter_timeout_sec", 60.0))
        self.history_limit: int = int(combat.get("history_limit", 50))
        self.dps_window_sec: float = float(combat.get("dps_window_sec", 1.0))

        # Map
        map_cfg = config_dict.get("map", {})
        self.default_zone: str = map_cfg.get("default_zone", "East Commonlands")
        self.auto_switch_zone: bool = bool(map_cfg.get("auto_switch_zone", True))
        self.max_breadcrumbs: int = int(map_cfg.get("max_breadcrumbs", 60))
        self.grid_width: int = int(map_cfg.get("grid_width", 58))
        self.grid_height: int = int(map_cfg.get("grid_height", 24))

        # Triggers
        self.triggers: List[Dict[str, Any]] = config_dict.get("triggers", [])

    def resolve_log_path(self) -> Path:
        """Find the active log file matching character and server, or latest log."""
        expected_filename = self.filename_pattern.format(
            character=self.character_name,
            server=self.server,
        )
        target_file = self.log_dir / expected_filename
        if target_file.exists():
            return target_file

        # Case-insensitive search or match any eqlog in directory
        if self.log_dir.exists():
            # Try lowercase / capitalized variations
            for file in self.log_dir.glob("eqlog_*.txt"):
                if file.name.lower() == expected_filename.lower():
                    return file

            # Check if any eqlog file exists in directory and return newest
            eqlogs = sorted(
                self.log_dir.glob("eqlog_*.txt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if eqlogs:
                return eqlogs[0]

        return target_file


def load_config(path: Optional[str or Path] = None) -> Config:
    """Load configuration from specified path, default locations, or built-in defaults."""
    search_paths: List[Path] = []
    if path:
        search_paths.append(Path(path))

    # Standard locations
    search_paths.extend([
        Path.cwd() / "config.yaml",
        Path.cwd() / "config.yml",
        Path.home() / ".config" / "ekco-parse" / "config.yaml",
        Path.home() / ".ekco-parse.yaml",
    ])

    for p in search_paths:
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                # Merge with default keys
                merged = dict(DEFAULT_CONFIG)
                for k, v in data.items():
                    if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                        merged[k] = {**merged[k], **v}
                    else:
                        merged[k] = v
                return Config(merged, config_path=p)
            except Exception as e:
                print(f"[Config] Warning: Failed to parse {p}: {e}. Using defaults.")

    return Config(DEFAULT_CONFIG)
