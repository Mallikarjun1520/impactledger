from uuid import UUID

import psycopg

from app.core.config import settings


def get_contribution_resources(
    organization_id: UUID,
    contribution_id: UUID,
) -> dict[str, list[dict]]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT
                       rb.id, rb.resource_type_id, rb.organization_id,
                       rb.batch_code, rb.quantity, rb.source_description,
                       rb.received_at, rb.location, rb.created_at, rb.updated_at
                  FROM resource_batches rb
                  JOIN purchase_orders po
                    ON po.id = rb.purchase_order_id
                   AND po.organization_id = rb.organization_id
                  JOIN commitments cm
                    ON cm.id = po.commitment_id
                   AND cm.organization_id = po.organization_id
                  JOIN allocations a
                    ON a.id = cm.allocation_id
                   AND a.organization_id = cm.organization_id
                 WHERE rb.organization_id = %s
                   AND a.organization_id = %s
                   AND a.contribution_id = %s
                 ORDER BY rb.created_at DESC
                """,
                (organization_id, organization_id, contribution_id),
            )
            batch_columns = [column.name for column in cursor.description]
            batch_rows = cursor.fetchall()
            batches = [dict(zip(batch_columns, row, strict=False)) for row in batch_rows]
            batch_ids = [row[0] for row in batch_rows]
            if not batch_ids:
                return {
                    "resource_batches": [],
                    "resource_events": [],
                    "distributions": [],
                }

            cursor.execute(
                """
                SELECT e.id, e.resource_batch_id, e.event_type::text AS event_type,
                       e.quantity, e.location, e.performed_by, e.reason,
                       e.transfer_id, e.created_at
                  FROM resource_events e
                  JOIN resource_batches rb
                    ON rb.id = e.resource_batch_id
                   AND rb.organization_id = e.organization_id
                 WHERE e.organization_id = %s
                   AND e.resource_batch_id = ANY(%s)
                 ORDER BY e.created_at DESC
                """,
                (organization_id, batch_ids),
            )
            event_columns = [column.name for column in cursor.description]
            events = [
                dict(zip(event_columns, row, strict=False))
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT id, relief_event_id, resource_batch_id, organization_id,
                       quantity, destination, beneficiary_count, notes,
                       created_by, created_at
                  FROM distributions
                 WHERE organization_id = %s
                   AND resource_batch_id = ANY(%s)
                 ORDER BY created_at DESC
                """,
                (organization_id, batch_ids),
            )
            distribution_columns = [column.name for column in cursor.description]
            distributions = [
                dict(zip(distribution_columns, row, strict=False))
                for row in cursor.fetchall()
            ]

    return {
        "resource_batches": batches,
        "resource_events": events,
        "distributions": distributions,
    }
