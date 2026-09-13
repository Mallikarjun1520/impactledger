
from uuid import UUID

import psycopg

from app.api.v1.schemas import DistributionCreate
from app.core.config import settings


def create_distribution(
    data: DistributionCreate,
    created_by: UUID,
    organization_id: UUID,
) -> str:
    target_org_id = organization_id

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:

            # Lock the batch row and verify it belongs to the authenticated
            # organization. This prevents cross-tenant access and serializes
            # concurrent distribution operations on the same batch.
            cursor.execute(
                """
                SELECT id
                FROM resource_batches
                WHERE id = %s
                  AND organization_id = %s
                FOR UPDATE
                """,
                (
                    data.resource_batch_id,
                    target_org_id,
                ),
            )

            batch = cursor.fetchone()

            if batch is None:
                raise ValueError(
                    "Resource batch not found or does not belong to organization"
                )

            # Calculate current inventory while the batch row is locked.
            cursor.execute(
                """
                SELECT
                    COALESCE(
                        SUM(
                            CASE
                                WHEN event_type IN (
                                    'RECEIVED',
                                    'TRANSFER_IN',
                                    'ADJUSTED'
                                )
                                THEN quantity

                                WHEN event_type IN (
                                    'TRANSFER_OUT',
                                    'DISTRIBUTED',
                                    'DAMAGED'
                                )
                                THEN -quantity

                                ELSE 0
                            END
                        ),
                        0
                    )
                FROM resource_events
                WHERE resource_batch_id = %s
                """,
                (data.resource_batch_id,),
            )

            available_quantity = cursor.fetchone()[0]

            if available_quantity < data.quantity:
                raise ValueError("Insufficient inventory")

            # Verify that the relief event belongs to the same organization.
            cursor.execute(
                """
                SELECT id
                FROM relief_events
                WHERE id = %s
                  AND organization_id = %s
                """,
                (
                    data.relief_event_id,
                    target_org_id,
                ),
            )

            relief_event = cursor.fetchone()

            if relief_event is None:
                raise ValueError(
                    "Relief event not found or does not belong to organization"
                )

            # Create the distribution record.
            cursor.execute(
                """
                INSERT INTO distributions (
                    relief_event_id,
                    resource_batch_id,
                    organization_id,
                    quantity,
                    destination,
                    beneficiary_count,
                    notes,
                    created_by
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (
                    data.relief_event_id,
                    data.resource_batch_id,
                    target_org_id,
                    data.quantity,
                    data.destination,
                    data.beneficiary_count,
                    data.notes,
                    created_by,
                ),
            )

            distribution_id = cursor.fetchone()[0]

            # Record the corresponding inventory event in the same
            # transaction so the distribution and inventory ledger
            # cannot become inconsistent.
            cursor.execute(
                """
                INSERT INTO resource_events (
                    resource_batch_id,
                    event_type,
                    quantity,
                    location,
                    performed_by,
                    reason
                )
                VALUES (
                    %s,
                    'DISTRIBUTED',
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    data.resource_batch_id,
                    data.quantity,
                    data.destination,
                    created_by,
                    f"Distribution {distribution_id}",
                ),
            )

            conn.commit()

            return str(distribution_id)


def get_distributions(
    organization_id: UUID,
) -> list[dict]:
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    relief_event_id,
                    resource_batch_id,
                    organization_id,
                    quantity,
                    destination,
                    beneficiary_count,
                    notes,
                    created_by,
                    created_at
                FROM distributions
                WHERE organization_id = %s
                ORDER BY created_at DESC
                """,
                (organization_id,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": str(row[0]),
                    "relief_event_id": str(row[1]),
                    "resource_batch_id": str(row[2]),
                    "organization_id": str(row[3]),
                    "quantity": float(row[4]),
                    "destination": row[5],
                    "beneficiary_count": row[6],
                    "notes": row[7],
                    "created_by": str(row[8]) if row[8] else None,
                    "created_at": row[9],
                }
                for row in rows
            ]


def get_inventory(
    resource_batch_id: UUID,
    organization_id: UUID,
) -> float | None:
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:

            # Verify that the requested batch belongs to the authenticated
            # organization before returning any inventory information.
            cursor.execute(
                """
                SELECT id
                FROM resource_batches
                WHERE id = %s
                  AND organization_id = %s
                """,
                (
                    resource_batch_id,
                    organization_id,
                ),
            )

            batch = cursor.fetchone()

            if batch is None:
                return None

            cursor.execute(
                """
                SELECT
                    COALESCE(
                        SUM(
                            CASE
                                WHEN event_type IN (
                                    'RECEIVED',
                                    'TRANSFER_IN',
                                    'ADJUSTED'
                                )
                                THEN quantity

                                WHEN event_type IN (
                                    'TRANSFER_OUT',
                                    'DISTRIBUTED',
                                    'DAMAGED'
                                )
                                THEN -quantity

                                ELSE 0
                            END
                        ),
                        0
                    )
                FROM resource_events
                WHERE resource_batch_id = %s
                """,
                (resource_batch_id,),
            )

            quantity = cursor.fetchone()[0]

            return float(quantity)