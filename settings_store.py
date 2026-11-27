"""Shared admin settings, stored in a small local JSON file.

Admin edits them; every viewer session reads them. Local file only (offline-safe).
Override the location with the DENGUE_SETTINGS_PATH environment variable.
"""
import json
import os
import tempfile
from datetime import datetime

DEFAULTS = {
    "stock": 70,          # regional stock, % of demand (30-100)
    "crews": 12,          # total spraying crews
    "cap_pct": 50,        # assumed bed capacity, % of historical peak demand
    "sim_crews": 8,       # crews in the what-if simulator
    "sim_wards": [],      # wards chosen for the simulator (empty = model picks)
    "ops_spray": 3,       # spray teams (action plan page)
    "ops_clean": 3,       # cleanup teams
    "ops_per": 1,         # wards per team per day
    "ops_medium": False,  # include Medium wards in the schedule
    "ops_start_issue": "",  # issue date the start date below belongs to
    "ops_start": "",        # admin-chosen schedule start date (ISO), "" = default
    "updated_at": "",
}


def _path():
    return os.environ.get("DENGUE_SETTINGS_PATH") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "admin_settings.json")


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass  # missing or corrupt file: fall back to defaults, never crash
    return cfg


def save(patch):
    """Merge `patch` into the stored settings (atomic write)."""
    cfg = load()
    cfg.update({k: v for k, v in patch.items() if k in DEFAULTS})
    cfg["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    path = _path()
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return cfg
