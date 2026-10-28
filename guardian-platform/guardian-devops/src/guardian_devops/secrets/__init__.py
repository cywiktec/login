"""Heuristic secret scanner and redaction. Heuristic: it reduces risk, it does not prove absence."""

import math
import re

PATTERNS = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "assignment": re.compile(
        r"""(?ix)\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*["']?([^\s"'$][^\s"']{7,})"""),
}


def _entropy(s):
    if not s:
        return 0.0
    return -sum(s.count(c) / len(s) * math.log2(s.count(c) / len(s)) for c in set(s))


def scan_text(text, name="<text>"):
    """Returns findings as (name, line_no, kind). Values are never included."""
    findings = []
    for no, line in enumerate(text.splitlines(), 1):
        for kind, rx in PATTERNS.items():
            m = rx.search(line)
            if not m:
                continue
            if kind == "assignment":
                value = m.group(2)
                if value.lower() in ("changeme", "example", "placeholder") or _entropy(value) < 2.5:
                    continue
            findings.append((name, no, kind))
    return findings


def redact(text):
    for kind, rx in PATTERNS.items():
        if kind == "assignment":
            text = rx.sub(lambda m: m.group(0).replace(m.group(2), "[REDACTED]"), text)
        else:
            text = rx.sub("[REDACTED]", text)
    return text


def scan_files(paths):
    """Unreadable files are reported as findings (fail closed)."""
    findings = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                findings.extend(scan_text(f.read(), str(p)))
        except (OSError, UnicodeDecodeError):
            findings.append((str(p), 0, "unreadable"))
    return findings


def require_env(names, environ):
    """Returns the missing or empty variable names; callers must refuse to start if non-empty."""
    return [n for n in names if not environ.get(n)]
