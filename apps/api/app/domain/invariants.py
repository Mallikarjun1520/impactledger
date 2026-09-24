"""Deterministic invariants (rulebook §7 financial, §8 physical, Rule 03).

Every check here is pure: inputs → boolean or raise. No I/O. The router layer
gathers the inputs (usually a SUM query) and calls the check.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


class InvariantViolation(ValueError):
    """Raised when a rulebook invariant would be violated."""

    def __init__(self, rule: str, message: str) -> None:
        super().__init__(f"[{rule}] {message}")
        self.rule = rule


# ---------------------------------------------------------------------------
# Financial invariants (rulebook §7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolBalance:
    contributed_confirmed: Decimal
    allocated_approved: Decimal

    @property
    def available(self) -> Decimal:
        return self.contributed_confirmed - self.allocated_approved


def check_pool_allocation(
    balance: PoolBalance, requested: Decimal
) -> None:
    """Rule §7.1: allocation cannot exceed available allocatable funds."""
    if requested <= 0:
        raise InvariantViolation("F.1", "Allocation amount must be positive")
    if requested > balance.available:
        raise InvariantViolation(
            "F.1",
            f"Requested allocation {requested} exceeds available "
            f"{balance.available} (contributed {balance.contributed_confirmed}, "
            f"already allocated {balance.allocated_approved}).",
        )


def check_restriction_compatibility(
    pool_scope: str,
    pool_initiative_id: str | None,
    pool_category: str | None,
    allocation_initiative_id: str | None,
    allocation_purpose_category: str | None,
) -> None:
    """Rule §7.2: restricted funds cannot escape their permitted scope."""
    if pool_scope == "UNRESTRICTED":
        return
    if pool_scope == "INITIATIVE":
        if allocation_initiative_id != pool_initiative_id:
            raise InvariantViolation(
                "F.2",
                f"Pool is initiative-restricted ({pool_initiative_id}); "
                f"allocation targeted {allocation_initiative_id}.",
            )
        return
    if pool_scope == "CATEGORY":
        if allocation_purpose_category != pool_category:
            raise InvariantViolation(
                "F.2",
                f"Pool is category-restricted ({pool_category}); allocation "
                f"targeted category {allocation_purpose_category}.",
            )
        return
    raise InvariantViolation("F.2", f"Unknown pool scope {pool_scope!r}")


@dataclass(frozen=True)
class AllocationBalance:
    approved_amount: Decimal
    committed_amount: Decimal

    @property
    def uncommitted(self) -> Decimal:
        return self.approved_amount - self.committed_amount


def check_commitment_capacity(
    balance: AllocationBalance, requested: Decimal
) -> None:
    """Rule §7.3: commitment cannot exceed available allocation capacity."""
    if requested <= 0:
        raise InvariantViolation("F.3", "Commitment amount must be positive")
    if requested > balance.uncommitted:
        raise InvariantViolation(
            "F.3",
            f"Requested commitment {requested} exceeds allocation capacity "
            f"{balance.uncommitted}.",
        )


@dataclass(frozen=True)
class PurchaseOrderBalance:
    total_amount: Decimal
    paid_amount: Decimal

    @property
    def outstanding(self) -> Decimal:
        return self.total_amount - self.paid_amount


def check_payment_within_po(
    balance: PurchaseOrderBalance, requested: Decimal
) -> None:
    """Rule §7.4: payment cannot exceed remaining valid commitment."""
    if requested <= 0:
        raise InvariantViolation("F.4", "Payment amount must be positive")
    if requested > balance.outstanding:
        raise InvariantViolation(
            "F.4",
            f"Payment {requested} exceeds PO outstanding {balance.outstanding} "
            f"(total {balance.total_amount}, already paid {balance.paid_amount}).",
        )


def check_refund_within_payment(paid: Decimal, refunded: Decimal, requested: Decimal) -> None:
    """Rule §7.5: refund cannot exceed corresponding payment."""
    if requested <= 0:
        raise InvariantViolation("F.5", "Refund amount must be positive")
    if refunded + requested > paid:
        raise InvariantViolation(
            "F.5",
            f"Refund {requested} would exceed original payment {paid} "
            f"(already refunded {refunded}).",
        )


def check_self_approval(created_by: str, approving: str, policy_allows_self: bool = False) -> None:
    """Segregation of duties (rulebook §15). Reject self-approval unless the
    org policy explicitly allows it."""
    if created_by == approving and not policy_allows_self:
        raise InvariantViolation(
            "S.1",
            "Segregation of duties: creator cannot approve their own action.",
        )


# ---------------------------------------------------------------------------
# Physical invariants (rulebook §8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchInventory:
    received: Decimal
    dispatched: Decimal
    delivered: Decimal
    distributed: Decimal
    transferred_out: Decimal
    transferred_in: Decimal
    lost: Decimal
    damaged: Decimal
    disposed: Decimal
    adjusted_delta: Decimal   # signed

    @property
    def in_transit(self) -> Decimal:
        """Dispatched but not yet delivered. Still ours."""
        return self.dispatched - self.delivered

    @property
    def total_inflow(self) -> Decimal:
        return self.received + self.transferred_in + self.adjusted_delta

    @property
    def permanent_outflow(self) -> Decimal:
        """Items no longer ours: distributed to beneficiaries, transferred to
        another organization, lost, or disposed. Damage is intentionally NOT
        an outflow — damaged items can still be counted; the org decides
        whether to dispose them."""
        return self.distributed + self.transferred_out + self.lost + self.disposed

    @property
    def remaining(self) -> Decimal:
        """Everything still ours (wherever it physically sits)."""
        return self.total_inflow - self.permanent_outflow

    @property
    def on_hand(self) -> Decimal:
        """Available at the source for a new outflow (dispatch, transfer_out,
        direct distribution). Dispatched-not-delivered items are treated as
        no longer at source."""
        return self.remaining - self.in_transit

    @property
    def available(self) -> Decimal:
        """Alias for ``on_hand`` used by capacity checks."""
        return self.on_hand

    @property
    def total_accounted(self) -> Decimal:
        """Conservation RHS: permanent outflows plus what is still ours."""
        return self.permanent_outflow + self.remaining


def check_non_negative_quantity(qty: Decimal) -> None:
    """Rule §8.1."""
    if qty < 0:
        raise InvariantViolation("P.1", f"Quantity cannot be negative ({qty}).")


def check_can_transfer_out(inv: BatchInventory, requested: Decimal) -> None:
    """Rule §8.2 / §8.3 / §8.5."""
    if requested <= 0:
        raise InvariantViolation("P.2", "Transfer/dispatch/distribution must be positive")
    if requested > inv.available:
        raise InvariantViolation(
            "P.2",
            f"Requested {requested} exceeds available quantity {inv.available}.",
        )


def check_can_deliver(inv: BatchInventory, requested: Decimal) -> None:
    """Rule §8.4: delivery cannot exceed in-transit quantity."""
    if requested <= 0:
        raise InvariantViolation("P.4", "Delivery must be positive")
    if requested > inv.in_transit:
        raise InvariantViolation(
            "P.4",
            f"Requested delivery {requested} exceeds in-transit {inv.in_transit}.",
        )


def check_conservation(inv: BatchInventory, tolerance: Decimal = Decimal("0.001")) -> None:
    """Rule §8.6 / §8.7 conservation identity.

    Enforces:
      * ``remaining >= 0``: permanent outflows may not exceed inflows.
      * ``in_transit >= 0``: cannot deliver more than has been dispatched.
      * ``total_inflow == total_accounted``: the identity itself, which is
        true by construction once the two non-negativity checks pass but is
        asserted for extra safety.
    """
    if inv.remaining < -tolerance:
        raise InvariantViolation(
            "P.6",
            f"Conservation broken: permanent outflows ({inv.permanent_outflow}) "
            f"exceed inflows ({inv.total_inflow}); remaining = {inv.remaining}.",
        )
    if inv.in_transit < -tolerance:
        raise InvariantViolation(
            "P.6",
            f"Conservation broken: delivered ({inv.delivered}) exceeds "
            f"dispatched ({inv.dispatched}).",
        )
    lhs = inv.total_inflow
    rhs = inv.total_accounted
    if abs(lhs - rhs) > tolerance:
        raise InvariantViolation(
            "P.6",
            f"Conservation identity failed: {lhs} != {rhs}.",
        )


def sum_amounts(values: Iterable[Decimal]) -> Decimal:
    total = Decimal("0")
    for v in values:
        total += v
    return total


__all__ = [
    "InvariantViolation",
    "PoolBalance",
    "AllocationBalance",
    "PurchaseOrderBalance",
    "BatchInventory",
    "check_pool_allocation",
    "check_restriction_compatibility",
    "check_commitment_capacity",
    "check_payment_within_po",
    "check_refund_within_payment",
    "check_self_approval",
    "check_non_negative_quantity",
    "check_can_transfer_out",
    "check_can_deliver",
    "check_conservation",
    "sum_amounts",
]
