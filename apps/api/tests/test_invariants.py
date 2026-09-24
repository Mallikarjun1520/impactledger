from decimal import Decimal

import pytest

from app.domain.invariants import (
    AllocationBalance,
    BatchInventory,
    InvariantViolation,
    PoolBalance,
    PurchaseOrderBalance,
    check_can_deliver,
    check_can_transfer_out,
    check_commitment_capacity,
    check_conservation,
    check_non_negative_quantity,
    check_payment_within_po,
    check_pool_allocation,
    check_refund_within_payment,
    check_restriction_compatibility,
    check_self_approval,
)


D = Decimal


# ---------- financial ----------


def test_pool_allocation_within_available_ok():
    check_pool_allocation(PoolBalance(D("1000"), D("300")), D("500"))


def test_pool_allocation_exceeds_available_rejected():
    with pytest.raises(InvariantViolation) as e:
        check_pool_allocation(PoolBalance(D("1000"), D("800")), D("300"))
    assert e.value.rule == "F.1"


def test_pool_allocation_zero_rejected():
    with pytest.raises(InvariantViolation):
        check_pool_allocation(PoolBalance(D("1000"), D("0")), D("0"))


def test_restriction_unrestricted_ignores_target():
    check_restriction_compatibility("UNRESTRICTED", None, None, "any-init", "any-cat")


def test_restriction_initiative_must_match():
    check_restriction_compatibility("INITIATIVE", "abc", None, "abc", None)
    with pytest.raises(InvariantViolation):
        check_restriction_compatibility("INITIATIVE", "abc", None, "def", None)


def test_restriction_category_must_match():
    check_restriction_compatibility("CATEGORY", None, "medical", None, "medical")
    with pytest.raises(InvariantViolation):
        check_restriction_compatibility("CATEGORY", None, "medical", None, "shelter")


def test_commitment_capacity_ok_and_reject():
    check_commitment_capacity(AllocationBalance(D("500"), D("100")), D("400"))
    with pytest.raises(InvariantViolation):
        check_commitment_capacity(AllocationBalance(D("500"), D("450")), D("100"))


def test_payment_within_po():
    check_payment_within_po(PurchaseOrderBalance(D("55000"), D("52000")), D("3000"))
    with pytest.raises(InvariantViolation):
        check_payment_within_po(PurchaseOrderBalance(D("55000"), D("52000")), D("3001"))


def test_refund_within_payment():
    check_refund_within_payment(D("1000"), D("200"), D("800"))
    with pytest.raises(InvariantViolation):
        check_refund_within_payment(D("1000"), D("200"), D("801"))


def test_self_approval_rejected_by_default():
    with pytest.raises(InvariantViolation) as e:
        check_self_approval("user-1", "user-1")
    assert e.value.rule == "S.1"


def test_self_approval_allowed_when_policy_permits():
    check_self_approval("user-1", "user-1", policy_allows_self=True)


def test_third_party_approval_ok():
    check_self_approval("user-1", "user-2")


# ---------- physical ----------


def _inv(**kw):
    defaults = dict(
        received=D("0"), dispatched=D("0"), delivered=D("0"),
        distributed=D("0"), transferred_out=D("0"), transferred_in=D("0"),
        lost=D("0"), damaged=D("0"), disposed=D("0"),
        adjusted_delta=D("0"),
    )
    defaults.update(kw)
    return BatchInventory(**defaults)


def test_non_negative_quantity():
    check_non_negative_quantity(D("0"))
    check_non_negative_quantity(D("5"))
    with pytest.raises(InvariantViolation):
        check_non_negative_quantity(D("-1"))


def test_transfer_out_within_available():
    check_can_transfer_out(_inv(received=D("500")), D("300"))
    with pytest.raises(InvariantViolation):
        check_can_transfer_out(_inv(received=D("500"), dispatched=D("300")), D("300"))


def test_delivery_within_in_transit():
    inv = _inv(received=D("500"), dispatched=D("200"), delivered=D("50"))
    check_can_deliver(inv, D("100"))
    with pytest.raises(InvariantViolation):
        check_can_deliver(inv, D("200"))


def test_conservation_holds_when_movements_balance():
    inv = _inv(
        received=D("500"),
        dispatched=D("300"),
        delivered=D("200"),
        distributed=D("100"),
    )
    check_conservation(inv)


def test_conservation_violation_surfaces():
    inv = _inv(received=D("500"), lost=D("501"))
    with pytest.raises(InvariantViolation):
        check_conservation(inv)
