"""Golden-file regression checks. A missing golden file is a failure, never silently created."""

import json
import os

UPDATE_ENV = "GUARDIAN_UPDATE_GOLDEN"


class GoldenMismatch(AssertionError):
    pass


def _canonical(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def check_golden(name, value, directory, update=None):
    """Compare `value` (JSON-serializable) with <directory>/<name>.json.
    update=True (or env GUARDIAN_UPDATE_GOLDEN=1) rewrites the file instead; review the diff."""
    if os.sep in name or name.startswith("."):
        raise ValueError("bad golden name")
    if update is None:
        update = os.environ.get(UPDATE_ENV) == "1"
    path = os.path.join(directory, f"{name}.json")
    actual = _canonical(value)
    if update:
        os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(actual)
        return
    try:
        with open(path, encoding="utf-8") as f:
            expected = f.read()
    except OSError:
        raise GoldenMismatch(f"golden file missing: {path} (run with {UPDATE_ENV}=1 to create)") from None
    if expected != actual:
        raise GoldenMismatch(f"output differs from {path}")


def check_text_golden(name, text, directory, update=None):
    check_golden(name, {"text": text}, directory, update)
