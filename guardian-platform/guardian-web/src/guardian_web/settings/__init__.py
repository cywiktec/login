"""Dashboard settings with role-based write access. Only the server enforces roles; the UI
hiding a button is not access control."""

ROLES = ("viewer", "operator", "admin")

DEFAULTS = {
    "refresh_s": 5,
    "theme": "light",
    "language": "pl",
    "require_command_confirmation": True,
    "session_timeout_min": 30,
}

_VALIDATORS = {
    "refresh_s": lambda v: isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 60,
    "theme": lambda v: v in ("light", "dark"),
    "language": lambda v: v in ("pl", "en"),
    "require_command_confirmation": lambda v: isinstance(v, bool),
    "session_timeout_min": lambda v: isinstance(v, int) and not isinstance(v, bool) and 5 <= v <= 480,
}

# Weakening safety-relevant settings needs admin; cosmetic ones need operator.
_MIN_ROLE = {"theme": "operator", "language": "operator", "refresh_s": "operator",
             "require_command_confirmation": "admin", "session_timeout_min": "admin"}


class SettingsError(ValueError):
    pass


class PermissionDenied(PermissionError):
    pass


class WebSettings:
    def __init__(self):
        self._values = dict(DEFAULTS)

    def get(self, key):
        if key not in _VALIDATORS:
            raise SettingsError(f"unknown setting {key!r}")
        return self._values[key]

    def set(self, key, value, role):
        if role not in ROLES:
            raise PermissionDenied(f"unknown role {role!r}")
        if key not in _VALIDATORS:
            raise SettingsError(f"unknown setting {key!r}")
        if ROLES.index(role) < ROLES.index(_MIN_ROLE[key]):
            raise PermissionDenied(f"{role} may not change {key}")
        if not _VALIDATORS[key](value):
            raise SettingsError(f"invalid value for {key}: {value!r}")
        self._values[key] = value

    def as_dict(self):
        return dict(self._values)
