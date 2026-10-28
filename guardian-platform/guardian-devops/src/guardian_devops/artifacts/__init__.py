"""Release artifact manifest: SHA-256 per file, verified before use."""

import hashlib
import json
import os


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(directory, version):
    files = {}
    for root, _dirs, names in os.walk(directory):
        for n in sorted(names):
            if n in ("MANIFEST.json", "MANIFEST.json.tmp"):
                continue
            full = os.path.join(root, n)
            files[os.path.relpath(full, directory).replace(os.sep, "/")] = sha256_file(full)
    return {"version": version, "files": dict(sorted(files.items()))}


def write_manifest(directory, version):
    path = os.path.join(directory, "MANIFEST.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(build_manifest(directory, version), f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


def verify(directory):
    """Returns a list of problems (missing, modified, extra files, bad manifest)."""
    path = os.path.join(directory, "MANIFEST.json")
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
        expected = manifest["files"]
        if not isinstance(expected, dict):
            raise TypeError
    except (OSError, ValueError, KeyError, TypeError):
        return ["manifest missing or invalid"]
    actual = build_manifest(directory, manifest.get("version"))["files"]
    problems = []
    for name, digest in expected.items():
        if name not in actual:
            problems.append(f"missing: {name}")
        elif actual[name] != digest:
            problems.append(f"modified: {name}")
    problems.extend(f"unexpected: {n}" for n in actual if n not in expected)
    return problems
