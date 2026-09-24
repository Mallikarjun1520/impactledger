"""Canonical JSON + SHA-256 for domain events (ADR-006, ADR-011).

We serialize with sorted object keys, no whitespace, and UTF-8. Numbers are
emitted as integers when integral or as strings for anything with decimal
component (avoids float non-determinism across languages). Timestamps must be
ISO-8601 UTC strings before hashing.

This scheme is intentionally simple and language-portable: JavaScript verifiers
in the browser reproduce the exact same bytes and hash.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID


def _canonical(value: Any) -> Any:
    """Return a JSON-friendly, deterministic representation of ``value``."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        # Reject floats outright: they cannot be reproduced deterministically
        # across languages. Callers should send Decimal or string.
        raise TypeError(
            "Refusing to hash a float: use Decimal or a numeric string instead"
        )
    if isinstance(value, Decimal):
        # Emit as string with the value's own scale, no trailing zeros stripped.
        # This preserves the exact digits the domain intended.
        return format(value.normalize(), "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        v = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in sorted(value.items(), key=lambda kv: kv[0])}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    raise TypeError(f"Unsupported type for canonical JSON: {type(value).__name__}")


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize ``payload`` to canonical UTF-8 bytes."""
    normalized = _canonical(payload)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,       # dict already sorted, but be explicit
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: Any) -> tuple[str, bytes]:
    """Return ``(hex_hash, canonical_bytes)`` for ``payload``."""
    body = canonical_json_bytes(payload)
    return sha256_hex(body), body


__all__ = [
    "canonical_json_bytes",
    "sha256_hex",
    "hash_payload",
]
