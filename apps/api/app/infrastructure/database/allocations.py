from decimal import Decimal
from uuid import UUID

import psycopg

from app.api.v1.schemas import AllocationCreate
from app.core.config import settings
from app.core.exceptions import (
    AllocationNotFoundError,
    ContributionNotFoundError,
    InvalidAllocationError,
)
from app.infrastructure.database.audit_logs import insert_audit_event


def create_allocation(
    organization_id: UUID,
    data: AllocationCreate,
    user_id: UUID,
) -> dict:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            # 1. Verify contribution exists and belongs to organization, locking row
            cursor.execute(
                """
                SELECT id, amount, status
                FROM contributions
                WHERE id = %s AND organization_id = %s
                FOR UPDATE
                """,
                (data.contribution_id, organization_id),
            )
            contribution_row = cursor.fetchone()
            if contribution_row is None:
                raise ContributionNotFoundError(
                    "Contribution not found or does not belong to organization"
                )

            contrib_amount = Decimal(str(contribution_row[1]))
            contrib_status = contribution_row[2]

            if contrib_status == "CANCELLED":
                raise InvalidAllocationError("Cannot allocate from a cancelled contribution")

            # 2. Check total existing allocations against contribution
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM allocations
                WHERE contribution_id = %s
                  AND status != 'CANCELLED'
                """,
                (data.contribution_id,),
            )
            allocated_amount = Decimal(str(cursor.fetchone()[0]))
            requested_amount = Decimal(str(data.amount))

            remaining = contrib_amount - allocated_amount
            if requested_amount > remaining:
                raise InvalidAllocationError(
                    f"Allocation exceeds available contribution amount. "
                    f"Remaining: {remaining}, Requested: {requested_amount}"
                )

            # 3. Create the allocation record
            cursor.execute(
                """
                INSERT INTO allocations (
                    contribution_id,
                    organization_id,
                    amount,
                    purpose,
                    status,
                    created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, contribution_id, organization_id, amount, purpose, status, created_by, created_at, updated_at
                """,
                (
                    data.contribution_id,
                    organization_id,
                    data.amount,
                    data.purpose,
                    data.status.value,
                    user_id,
                ),
            )
            row = cursor.fetchone()
            columns = [col.name for col in cursor.description]
            allocation = dict(zip(columns, row))
            insert_audit_event(
                cursor,
                organization_id=organization_id,
                event_type="ADMIN_ACTION",
                user_id=user_id,
                details={
                    "action": "ALLOCATION_RECORDED",
                    "entity_type": "allocation",
                    "entity_id": str(allocation["id"]),
                    "contribution_id": str(data.contribution_id),
                    "amount": str(data.amount),
                },
            )

        connection.commit()

    return allocation


def list_allocations(
    organization_id: UUID,
    contribution_id: UUID | None = None,
) -> list[dict]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            if contribution_id is not None:
                # Ensure contribution belongs to organization
                cursor.execute(
                    """
                    SELECT id
                    FROM contributions
                    WHERE id = %s AND organization_id = %s
                    """,
                    (contribution_id, organization_id),
                )
                if cursor.fetchone() is None:
                    raise ContributionNotFoundError(
                        "Contribution not found or does not belong to organization"
                    )

                cursor.execute(
                    """
                    SELECT id, contribution_id, organization_id, amount, purpose, status, created_by, created_at, updated_at
                    FROM allocations
                    WHERE organization_id = %s AND contribution_id = %s
                    ORDER BY created_at DESC
                    """,
                    (organization_id, contribution_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, contribution_id, organization_id, amount, purpose, status, created_by, created_at, updated_at
                    FROM allocations
                    WHERE organization_id = %s
                    ORDER BY created_at DESC
                    """,
                    (organization_id,),
                )

            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def get_allocation(organization_id: UUID, allocation_id: UUID) -> dict | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, contribution_id, organization_id, amount, purpose, status, created_by, created_at, updated_at
                FROM allocations
                WHERE id = %s AND organization_id = %s
                """,
                (allocation_id, organization_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [col.name for col in cursor.description]

    return dict(zip(columns, row))
