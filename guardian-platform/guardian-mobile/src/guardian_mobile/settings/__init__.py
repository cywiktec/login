"""Validated, atomically persisted app settings. Invalid values are rejected, never stored."""

import json
import os
import tempfile

DEFAULTS = {
    "base_url": "",
    "language": "pl",
    "confirm_commands": True,
    "stale_after_s": 5.0,
    "units": "metric",
}

_VALIDATORS = {
    "base_url": lambda v: isinstance(v, str) and (v == "" or v.startswith("https://")),
    "language": lambda v: v in ("pl", "en"),
    "confirm_commands": lambda v: isinstance(v, bool),
    "stale_after_s": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and 1 <= v <= 60,
    "units": lambda v: v in ("metric", "imperial"),
}


class SettingsError(ValueError):
    pass


class Settings:
    def __init__(self, path=None):
        self.path = path
        self._values = dict(DEFAULTS)
        if path and os.path.exists(path):
            self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return  # corrupt file: keep defaults
        if isinstance(data, dict):
            for key, value in data.items():
                if key in _VALIDATORS and _VALIDATORS[key](value):
                    self._values[key] = value

    def get(self, key):
        if key not in _VALIDATORS:
            raise SettingsError(f"unknown setting {key!r}")
        return self._values[key]

    def set(self, key, value):
        if key not in _VALIDATORS:
            raise SettingsError(f"unknown setting {key!r}")
        if not _VALIDATORS[key](value):
            raise SettingsError(f"invalid value for {key}: {value!r}")
        self._values[key] = value
        self._save()

    def as_dict(self):
        return dict(self._values)

    def _save(self):
        if not self.path:
            return
        directory = os.path.dirname(os.path.abspath(self.path))
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._values, f)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
