import psycopg

from app.api.v1.schemas import DistributionCreate
from app.core.config import settings


def create_distribution(data: DistributionCreate) -> str:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:

            # 1. Check available quantity in the resource batch
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
                raise ValueError(
                    f"Insufficient resource quantity. "
                    f"Available: {available_quantity}, "
                    f"Requested: {data.quantity}"
                )

            # 2. Create the distribution
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    data.relief_event_id,
                    data.resource_batch_id,
                    data.organization_id,
                    data.quantity,
                    data.destination,
                    data.beneficiary_count,
                    data.notes,
                    data.created_by,
                ),
            )

            distribution_id = cursor.fetchone()[0]

            # 3. Record the corresponding resource event
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
                    data.created_by,
                    f"Distribution {distribution_id}",
                ),
            )

        # 4. Commit both operations together
        connection.commit()

    return str(distribution_id)


def get_distributions() -> list[dict]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
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
                ORDER BY created_at DESC
                """
            )

            columns = [column.name for column in cursor.description]
            rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]
def get_inventory(resource_batch_id: str) -> float:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
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