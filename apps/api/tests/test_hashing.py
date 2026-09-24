from decimal import Decimal
from uuid import UUID

import pytest

from app.domain.hashing import canonical_json_bytes, hash_payload, sha256_hex


def test_canonical_sorts_keys():
    a = {"z": 1, "a": 2}
    b = {"a": 2, "z": 1}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_canonical_rejects_float():
    with pytest.raises(TypeError):
        canonical_json_bytes({"x": 1.5})


def test_canonical_accepts_decimal():
    payload = {"amount": Decimal("100.50")}
    b = canonical_json_bytes(payload)
    assert b == b'{"amount":"100.5"}'


def test_canonical_serializes_uuid():
    uid = UUID("12345678-1234-5678-1234-567812345678")
    b = canonical_json_bytes({"id": uid})
    assert b == b'{"id":"12345678-1234-5678-1234-567812345678"}'


def test_canonical_serializes_nested():
    payload = {"outer": {"inner": [1, 2, 3], "flag": True}}
    b = canonical_json_bytes(payload)
    assert b == b'{"outer":{"flag":true,"inner":[1,2,3]}}'


def test_hash_payload_deterministic():
    payload = {"k": "v", "n": 5, "list": [{"b": 2, "a": 1}]}
    h1, _ = hash_payload(payload)
    h2, _ = hash_payload({"list": [{"a": 1, "b": 2}], "n": 5, "k": "v"})
    assert h1 == h2 == sha256_hex(canonical_json_bytes(payload))


def test_sha256_hex_length():
    assert len(sha256_hex(b"anything")) == 64
