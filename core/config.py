import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "HandBrakeAutoAV1"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "output_dir": "",
    "use_same_dir_as_source": True,
    "auto_convert_on_drop": True,
    "quality_rf": 26,
    "encoder_preset": "6",
    "output_container": "mkv",
    "audio_passthrough": True,
    "all_subtitles": True,
    "keep_chapters": True,
    "skip_existing_av1": True,
    "recursive_folder_scan": False,
    "github_repo": "Bonfiretm/handbrake-auto-av1",
    "check_updates_on_startup": True,
}


def load_config() -> dict:
    """Load config from disk or return defaults."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    """Save config to disk."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Fehler beim Speichern der Konfiguration: {e}")
        return False
