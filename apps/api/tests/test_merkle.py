import hashlib
import pytest

from app.services.merkle import (
    leaf_hash,
    merkle_proof,
    merkle_proof_hex,
    merkle_root,
    merkle_root_hex,
    node_hash,
    verify_proof,
)


def _hex(n: int) -> str:
    return hashlib.sha256(str(n).encode()).hexdigest()


def test_root_single_leaf_matches_leaf_hash():
    h = _hex(1)
    assert merkle_root_hex([h]) == leaf_hash(h).hex()


def test_root_two_leaves_matches_hand_computation():
    a, b = _hex(1), _hex(2)
    la, lb = leaf_hash(a), leaf_hash(b)
    expected = node_hash(la, lb).hex()
    assert merkle_root_hex([a, b]) == expected


def test_root_odd_leaves_duplicates_last():
    a, b, c = _hex(1), _hex(2), _hex(3)
    la, lb, lc = leaf_hash(a), leaf_hash(b), leaf_hash(c)
    level1 = [node_hash(la, lb), node_hash(lc, lc)]
    expected = node_hash(level1[0], level1[1]).hex()
    assert merkle_root_hex([a, b, c]) == expected


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 8, 9, 15, 16, 17, 100])
def test_proof_round_trip(size):
    hashes = [_hex(i) for i in range(size)]
    leaves = [leaf_hash(h) for h in hashes]
    root = merkle_root(leaves)
    for idx in range(size):
        proof = merkle_proof(leaves, idx)
        assert verify_proof(leaves[idx], idx, proof, root)


def test_proof_wrong_leaf_fails():
    hashes = [_hex(i) for i in range(8)]
    leaves = [leaf_hash(h) for h in hashes]
    root = merkle_root(leaves)
    proof = merkle_proof(leaves, 3)
    wrong_leaf = leaf_hash(_hex(999))
    assert not verify_proof(wrong_leaf, 3, proof, root)


def test_merkle_proof_hex_serialization_shape():
    hashes = [_hex(i) for i in range(4)]
    proof = merkle_proof_hex(hashes, 2)
    for step in proof:
        assert set(step.keys()) == {"sibling", "is_right"}
        assert len(step["sibling"]) == 64
        assert isinstance(step["is_right"], bool)


def test_proof_out_of_range_raises():
    with pytest.raises(IndexError):
        merkle_proof([leaf_hash(_hex(0))], 1)


def test_proof_empty_tree_raises():
    with pytest.raises(ValueError):
        merkle_proof([], 0)
