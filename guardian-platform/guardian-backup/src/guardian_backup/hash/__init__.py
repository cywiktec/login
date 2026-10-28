"""SHA-256 helpers."""

import hashlib
import hmac
import json


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def canonical_json(obj):
    """Stable serialization so the same data always hashes the same."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_obj(obj):
    return sha256_bytes(canonical_json(obj))


def verify(expected, actual):
    """Constant-time comparison of hex digests."""
    return isinstance(expected, str) and isinstance(actual, str) and hmac.compare_digest(expected, actual)
