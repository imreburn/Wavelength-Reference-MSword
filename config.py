"""Settings constants and JSON settings-file I/O (no GUI, no pandas)."""

import copy
import json
import os

from paths import settings_dir


# Allowed choices for every "number of decimals" dropdown.
DECIMAL_CHOICES = ["0", "1", "2", "3", "4", "5"]

# The two sheets the user can target; exactly one is created per run.
TARGET_TRAVELER = "Traveler Sheet"
TARGET_CERT = "Certificate Sheet"

# Built-in defaults for every input field. These are used to write
# ``settings/default.json`` on first run and as a fallback for any key a saved
# settings file leaves out, so the app always has a complete set of values.
DEFAULT_SETTINGS = {
    "source": "Keysight N7778C Tunable Laser Source",
    "detector": "Keysight N7748A Power Meter",
    "part_num": "",
    "il_wavelength": "",
    "certified_by": "",
    "traveler_filename": "traveler_sheet_filled.docx",
    "traveler_decimals": {"wavelength": 2, "il": 1, "depth": 2, "width": 1},
    "cert_filename": "certificate_sheet_filled.docx",
    "cert_decimals": {"wavelength": 1, "il": 1, "depth": 1, "width": 1},
    "extras": ["", "", "", "", ""],
}

# The settings file selected by default when the app starts.
DEFAULT_SETTINGS_FILE = "default.json"


def ensure_default_settings():
    """Make sure ``settings/default.json`` exists, creating it (and the folder)
    from DEFAULT_SETTINGS the first time the app runs."""
    os.makedirs(settings_dir(), exist_ok=True)
    path = os.path.join(settings_dir(), DEFAULT_SETTINGS_FILE)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)


def list_setting_files():
    """Return the sorted ``*.json`` filenames in the settings folder, with
    ``default.json`` first if present."""
    if not os.path.isdir(settings_dir()):
        return []
    files = sorted(
        f for f in os.listdir(settings_dir()) if f.lower().endswith(".json")
    )
    if DEFAULT_SETTINGS_FILE in files:
        files.remove(DEFAULT_SETTINGS_FILE)
        files.insert(0, DEFAULT_SETTINGS_FILE)
    return files


def load_settings(name):
    """Load ``settings/<name>`` merged over DEFAULT_SETTINGS so missing keys fall
    back to the built-in defaults. Returns a full settings dict; on any read/parse
    error it falls back to the built-in defaults."""
    data = copy.deepcopy(DEFAULT_SETTINGS)
    try:
        with open(os.path.join(settings_dir(), name), "r", encoding="utf-8") as f:
            loaded = json.load(f)
        for key, value in loaded.items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key].update(value)  # merge nested (e.g. decimal counts)
            else:
                data[key] = value
    except Exception:
        pass  # missing or invalid file: keep the built-in defaults
    return data
