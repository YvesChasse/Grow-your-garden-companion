"""Versioned local preferences, validated on read and atomically replaced on write."""
import json
import os
from pathlib import Path

DEFAULTS = {
    "version": 1, "watchlist": [], "catalog": {}, "panel_visible": True,
    "bar_visible": False, "notifications": True, "sound": False,
    "repeat_alerts": True, "start_in_tray": False, "opacity": 96,
    "weather_alerts": False, "traveler_alerts": False, "bonus_alerts": False,
    "world_overlay": True,
    "panel_geometry": [], "bar_geometry": [], "window_geometry": [],
}


def preferences_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
    return base / "GrowYourGardenCompanion" / "preferences.json"


class Preferences:
    def __init__(self, path: Path | None = None):
        self.path = path or preferences_path()
        self.values = {**DEFAULTS, "watchlist": [], "catalog": {}}
        self.warning = ""
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or raw.get("version", 1) != 1:
                raise ValueError("Unsupported preferences format")
            for key, default in DEFAULTS.items():
                value = raw.get(key, default)
                if isinstance(default, bool) and isinstance(value, bool):
                    self.values[key] = value
            watchlist = raw.get("watchlist", [])
            if isinstance(watchlist, list):
                self.values["watchlist"] = sorted({x for x in watchlist if isinstance(x, str) and 0 < len(x) < 240})
            catalog = raw.get("catalog", {})
            if isinstance(catalog, dict):
                self.values["catalog"] = {k: v for k, v in catalog.items()
                                          if isinstance(k, str) and isinstance(v, dict)
                                          and isinstance(v.get("name"), str)
                                          and v.get("category") in {"seeds", "eggs", "gear", "event", "traveler"}}
            opacity = raw.get("opacity", 96)
            if isinstance(opacity, int) and not isinstance(opacity, bool):
                self.values["opacity"] = max(55, min(100, opacity))
            for key in ("panel_geometry", "bar_geometry", "window_geometry"):
                geometry = raw.get(key, [])
                if isinstance(geometry, list) and len(geometry) == 4 and all(type(x) is int for x in geometry):
                    self.values[key] = geometry
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as error:
            self.warning = f"Preferences could not be read; using defaults. {error}"

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.values, indent=2, ensure_ascii=False), encoding="utf-8")
            temporary.replace(self.path)
            self.warning = ""
            return True
        except OSError as error:
            self.warning = f"Preferences could not be saved: {error}"
            return False
