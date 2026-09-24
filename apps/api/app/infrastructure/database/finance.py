"""Persistence for initiatives, fund_pools, contributions-in-pools, allocations,
commitments, purchase_orders, payments. Uses raw psycopg to match the existing
codebase style.

All write methods return the operational row's UUID + the domain-event
identifiers so callers can compose provenance edges.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import settings
from app.domain.events import DomainEventInput, DomainEventType
from app.domain.invariants import (
    AllocationBalance,
    PoolBalance,
    PurchaseOrderBalance,
    check_commitment_capacity,
    check_payment_within_po,
    check_pool_allocation,
    check_restriction_compatibility,
    check_self_approval,
)
from app.infrastructure.database.domain_events import _record_in_txn


# ---------- helpers ----------


def _fetch_pool_balance(cur: psycopg.Cursor, org_id: UUID, pool_id: UUID) -> PoolBalance:
    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
          FROM contributions
         WHERE organization_id = %s
           AND fund_pool_id = %s
           AND status = 'CONFIRMED'
        """,
        (org_id, pool_id),
    )
    contributed = Decimal(cur.fetchone()[0])
    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
          FROM allocations
         WHERE organization_id = %s
           AND fund_pool_id = %s
           AND status = 'APPROVED'
        """,
        (org_id, pool_id),
    )
    allocated = Decimal(cur.fetchone()[0])
    return PoolBalance(contributed_confirmed=contributed, allocated_approved=allocated)


def _fetch_pool_scope(cur: psycopg.Cursor, org_id: UUID, pool_id: UUID) -> dict[str, Any]:
    cur.execute(
        """
        SELECT restriction_scope::text, initiative_id::text, category
          FROM fund_pools
         WHERE id = %s AND organization_id = %s
        """,
        (pool_id, org_id),
    )
    row = cur.fetchone()
    if row is None:
        raise LookupError(f"Fund pool {pool_id} not found in org {org_id}")
    return {
        "scope": row[0],
        "initiative_id": row[1],
        "category": row[2],
    }


# ---------- initiatives ----------


def create_initiative(
    org_id: UUID,
    user_id: UUID,
    name: str,
    slug: str,
    description: str | None,
    category: str | None,
) -> dict[str, Any]:
    initiative_id = uuid4()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO initiatives (
                        id, organization_id, name, slug, description,
                        category, status, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'DRAFT', %s)
                    RETURNING id, organization_id, name, slug, description,
                              category, status::text, starts_at, closes_at,
                              created_at
                    """,
                    (initiative_id, org_id, name, slug, description, category, user_id),
                )
                row = cursor.fetchone()
    return dict(
        id=row[0], organization_id=row[1], name=row[2], slug=row[3],
        description=row[4], category=row[5], status=row[6],
        starts_at=row[7], closes_at=row[8], created_at=row[9],
    )


# ---------- fund pools ----------


def create_fund_pool(
    org_id: UUID,
    user_id: UUID,
    name: str,
    slug: str,
    description: str | None,
    restriction_scope: str,
    initiative_id: UUID | None,
    category: str | None,
    currency: str,
) -> dict[str, Any]:
    pool_id = uuid4()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO fund_pools (
                        id, organization_id, name, slug, description,
                        restriction_scope, initiative_id, category, currency,
                        created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, organization_id, name, slug, description,
                              restriction_scope::text, initiative_id, category,
                              currency, is_closed, created_at
                    """,
                    (
                        pool_id, org_id, name, slug, description,
                        restriction_scope, initiative_id, category, currency,
                        user_id,
                    ),
                )
                row = cursor.fetchone()

                _record_in_txn(
                    connection,
                    DomainEventInput(
                        organization_id=org_id,
                        event_type=DomainEventType.FUND_POOL_CREATED,
                        aggregate_type="fund_pool",
                        aggregate_id=pool_id,
                        performed_by=user_id,
                        payload={
                            "name": name,
                            "slug": slug,
                            "restriction_scope": restriction_scope,
                            "initiative_id": str(initiative_id) if initiative_id else None,
                            "category": category,
                            "currency": currency,
                        },
                    ),
                )
    return dict(
        id=row[0], organization_id=row[1], name=row[2], slug=row[3],
        description=row[4], restriction_scope=row[5],
        initiative_id=row[6], category=row[7], currency=row[8],
        is_closed=row[9], created_at=row[10],
    )


# ---------- contributions into pools ----------


def record_pool_contribution(
    org_id: UUID,
    user_id: UUID,
    pool_id: UUID,
    amount: Decimal,
    currency: str,
    visibility: str,
    contributor_metadata: dict | None,
    external_reference: str | None,
) -> dict[str, Any]:
    contribution_id = uuid4()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                scope = _fetch_pool_scope(cursor, org_id, pool_id)
                cursor.execute(
                    """
                    INSERT INTO contributions (
                        id, organization_id, contributor_user_id, amount,
                        currency, visibility, status, received_at,
                        fund_pool_id, restriction_scope, initiative_id,
                        category, contributor_metadata, external_reference
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, 'CONFIRMED', NOW(),
                        %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING id, amount, currency, status, received_at, created_at
                    """,
                    (
                        contribution_id, org_id, user_id, amount,
                        currency, visibility,
                        pool_id, scope["scope"],
                        scope["initiative_id"], scope["category"],
                        Jsonb(contributor_metadata or {}),
                        external_reference,
                    ),
                )
                row = cursor.fetchone()

                _record_in_txn(
                    connection,
                    DomainEventInput(
                        organization_id=org_id,
                        event_type=DomainEventType.CONTRIBUTION_RECORDED,
                        aggregate_type="contribution",
                        aggregate_id=contribution_id,
                        performed_by=user_id,
                        payload={
                            "amount": str(amount),
                            "currency": currency,
                            "visibility": visibility,
                            "fund_pool_id": str(pool_id),
                            "restriction_scope": scope["scope"],
                        },
                    ),
                )
    return dict(id=row[0], amount=row[1], currency=row[2], status=row[3],
                received_at=row[4], created_at=row[5], fund_pool_id=pool_id)


# ---------- allocations from pools ----------


def record_pool_allocation(
    org_id: UUID,
    user_id: UUID,
    pool_id: UUID,
    amount: Decimal,
    purpose: str,
    initiative_id: UUID | None,
    purpose_category: str | None,
) -> dict[str, Any]:
    allocation_id = uuid4()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                # Restriction check + capacity check under the same txn snapshot.
                scope = _fetch_pool_scope(cursor, org_id, pool_id)
                check_restriction_compatibility(
                    pool_scope=scope["scope"],
                    pool_initiative_id=scope["initiative_id"],
                    pool_category=scope["category"],
                    allocation_initiative_id=str(initiative_id) if initiative_id else None,
                    allocation_purpose_category=purpose_category,
                )
                balance = _fetch_pool_balance(cursor, org_id, pool_id)
                check_pool_allocation(balance, amount)

                cursor.execute(
                    """
                    INSERT INTO allocations (
                        id, organization_id, contribution_id, amount, purpose,
                        status, created_by, fund_pool_id, initiative_id,
                        purpose_category, currency
                    ) VALUES (
                        %s, %s, NULL, %s, %s,
                        'APPROVED', %s, %s, %s,
                        %s, 'INR'
                    )
                    """,
                    (
                        allocation_id, org_id, amount, purpose,
                        user_id, pool_id, initiative_id, purpose_category,
                    ),
                )
                _record_in_txn(
                    connection,
                    DomainEventInput(
                        organization_id=org_id,
                        event_type=DomainEventType.ALLOCATION_RECORDED,
                        aggregate_type="allocation",
                        aggregate_id=allocation_id,
                        performed_by=user_id,
                        payload={
                            "amount": str(amount),
                            "purpose": purpose,
                            "fund_pool_id": str(pool_id),
                            "initiative_id": str(initiative_id) if initiative_id else None,
                            "purpose_category": purpose_category,
                        },
                    ),
                )
    return dict(id=allocation_id, amount=amount, purpose=purpose,
                fund_pool_id=pool_id, initiative_id=initiative_id)


# ---------- commitments ----------


def create_commitment(
    org_id: UUID,
    user_id: UUID,
    allocation_id: UUID,
    vendor_id: UUID | None,
    amount: Decimal,
    description: str,
) -> dict[str, Any]:
    commitment_id = uuid4()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT amount FROM allocations
                     WHERE id = %s AND organization_id = %s AND status = 'APPROVED'
                     FOR UPDATE
                    """,
                    (allocation_id, org_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise LookupError("Allocation not found or not APPROVED")
                approved = Decimal(row[0])

                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                      FROM commitments
                     WHERE allocation_id = %s AND status = 'ACTIVE'
                    """,
                    (allocation_id,),
                )
                committed = Decimal(cursor.fetchone()[0])
                check_commitment_capacity(
                    AllocationBalance(approved_amount=approved, committed_amount=committed),
                    amount,
                )

                cursor.execute(
                    """
                    INSERT INTO commitments (
                        id, organization_id, allocation_id, vendor_id,
                        amount, description, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, organization_id, allocation_id, vendor_id,
                              amount, currency, description, status::text, created_at
                    """,
                    (
                        commitment_id, org_id, allocation_id, vendor_id,
                        amount, description, user_id,
                    ),
                )
                r = cursor.fetchone()

                _record_in_txn(
                    connection,
                    DomainEventInput(
                        organization_id=org_id,
                        event_type=DomainEventType.COMMITMENT_CREATED,
                        aggregate_type="commitment",
                        aggregate_id=commitment_id,
                        performed_by=user_id,
                        payload={
                            "allocation_id": str(allocation_id),
                            "vendor_id": str(vendor_id) if vendor_id else None,
                            "amount": str(amount),
                            "description": description,
                        },
                    ),
                )

    return dict(
        id=r[0], organization_id=r[1], allocation_id=r[2], vendor_id=r[3],
        amount=r[4], currency=r[5], description=r[6], status=r[7], created_at=r[8],
    )


# ---------- purchase orders ----------


def create_purchase_order(
    org_id: UUID,
    user_id: UUID,
    commitment_id: UUID,
    vendor_id: UUID,
    po_number: str,
    total_amount: Decimal,
    tax_amount: Decimal,
    shipping_amount: Decimal,
    line_items: list[dict],
) -> dict[str, Any]:
    po_id = uuid4()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT amount FROM commitments
                     WHERE id = %s AND organization_id = %s AND status = 'ACTIVE'
                     FOR UPDATE
                    """,
                    (commitment_id, org_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise LookupError("Commitment not found or not ACTIVE")
                if Decimal(total_amount) > Decimal(row[0]):
                    raise ValueError(
                        "PO total cannot exceed the underlying commitment amount"
                    )

                cursor.execute(
                    """
                    INSERT INTO purchase_orders (
                        id, organization_id, commitment_id, vendor_id, po_number,
                        total_amount, tax_amount, shipping_amount, line_items,
                        created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, organization_id, po_number, status::text,
                              total_amount, created_at
                    """,
                    (
                        po_id, org_id, commitment_id, vendor_id, po_number,
                        total_amount, tax_amount, shipping_amount,
                        Jsonb(line_items),
                        user_id,
                    ),
                )
                r = cursor.fetchone()

                _record_in_txn(
                    connection,
                    DomainEventInput(
                        organization_id=org_id,
                        event_type=DomainEventType.PURCHASE_ORDER_CREATED,
                        aggregate_type="purchase_order",
                        aggregate_id=po_id,
                        performed_by=user_id,
                        payload={
                            "po_number": po_number,
                            "commitment_id": str(commitment_id),
                            "vendor_id": str(vendor_id),
                            "total_amount": str(total_amount),
                            "line_items": line_items,
                        },
                    ),
                )

    return dict(id=r[0], organization_id=r[1], po_number=r[2],
                status=r[3], total_amount=r[4], created_at=r[5])


def approve_purchase_order(
    org_id: UUID,
    approving_user_id: UUID,
    po_id: UUID,
    policy_allows_self: bool = False,
) -> None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT created_by, status::text
                      FROM purchase_orders
                     WHERE id = %s AND organization_id = %s
                     FOR UPDATE
                    """,
                    (po_id, org_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise LookupError("Purchase order not found")
                created_by, status = row
                if status not in ("DRAFT", "AWAITING_APPROVAL"):
                    raise ValueError(f"PO cannot be approved from status {status}")
                check_self_approval(str(created_by), str(approving_user_id),
                                    policy_allows_self=policy_allows_self)
                cursor.execute(
                    """
                    UPDATE purchase_orders
                       SET status = 'APPROVED',
                           approved_by = %s,
                           approved_at = NOW(),
                           updated_at = NOW()
                     WHERE id = %s
                    """,
                    (approving_user_id, po_id),
                )
                _record_in_txn(
                    connection,
                    DomainEventInput(
                        organization_id=org_id,
                        event_type=DomainEventType.PURCHASE_ORDER_APPROVED,
                        aggregate_type="purchase_order",
                        aggregate_id=po_id,
                        performed_by=approving_user_id,
                        payload={"approved_by": str(approving_user_id)},
                    ),
                )


# ---------- payments ----------


def record_payment(
    org_id: UUID,
    user_id: UUID,
    po_id: UUID,
    amount: Decimal,
    method: str,
    reference: str | None,
) -> dict[str, Any]:
    payment_id = uuid4()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT total_amount, status::text
                      FROM purchase_orders
                     WHERE id = %s AND organization_id = %s
                     FOR UPDATE
                    """,
                    (po_id, org_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise LookupError("Purchase order not found")
                total, status = row
                if status not in ("APPROVED", "RECEIVED"):
                    raise ValueError(
                        f"Cannot pay against PO in status {status}; must be APPROVED or RECEIVED"
                    )

                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                      FROM payments
                     WHERE purchase_order_id = %s
                       AND status = 'COMPLETED'
                    """,
                    (po_id,),
                )
                paid = Decimal(cursor.fetchone()[0])
                check_payment_within_po(
                    PurchaseOrderBalance(total_amount=Decimal(total),
                                         paid_amount=paid),
                    amount,
                )

                cursor.execute(
                    """
                    INSERT INTO payments (
                        id, organization_id, purchase_order_id, amount,
                        method, status, reference, paid_at, created_by
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, 'COMPLETED', %s, NOW(), %s
                    )
                    RETURNING id, purchase_order_id, amount, method::text,
                              status::text, reference, paid_at, created_at
                    """,
                    (payment_id, org_id, po_id, amount, method, reference, user_id),
                )
                r = cursor.fetchone()

                _record_in_txn(
                    connection,
                    DomainEventInput(
                        organization_id=org_id,
                        event_type=DomainEventType.PAYMENT_RECORDED,
                        aggregate_type="payment",
                        aggregate_id=payment_id,
                        performed_by=user_id,
                        payload={
                            "purchase_order_id": str(po_id),
                            "amount": str(amount),
                            "method": method,
                            "reference": reference,
                        },
                    ),
                )

    return dict(id=r[0], purchase_order_id=r[1], amount=r[2], method=r[3],
                status=r[4], reference=r[5], paid_at=r[6], created_at=r[7])
