from uuid import UUID

import psycopg

from app.api.v1.schemas import (
    ResourceBatchCreate,
    ResourceEventCreate,
    ResourceTypeCreate,
)
from app.core.config import settings
from app.core.exceptions import (
    DuplicateBatchCodeError,
    DuplicateResourceTypeError,
    InsufficientInventoryError,
    ResourceBatchNotFoundError,
    ResourceTypeNotFoundError,
)


# ---------------------------------------------------------------------------
# Resource Types
# ---------------------------------------------------------------------------


def create_resource_type(organization_id: UUID, data: ResourceTypeCreate) -> dict:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO resource_types (
                        organization_id,
                        name,
                        unit,
                        description
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, organization_id, name, unit, description, created_at, updated_at
                    """,
                    (
                        organization_id,
                        data.name,
                        data.unit,
                        data.description,
                    ),
                )
            except psycopg.errors.UniqueViolation:
                raise DuplicateResourceTypeError(
                    f"Resource type '{data.name}' already exists in this organization"
                )

            row = cursor.fetchone()
            columns = [col.name for col in cursor.description]

    return dict(zip(columns, row))


def list_resource_types(organization_id: UUID) -> list[dict]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, organization_id, name, unit, description, created_at, updated_at
                FROM resource_types
                WHERE organization_id = %s
                ORDER BY name ASC
                """,
                (organization_id,),
            )
            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def get_resource_type(organization_id: UUID, resource_type_id: UUID) -> dict | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, organization_id, name, unit, description, created_at, updated_at
                FROM resource_types
                WHERE id = %s AND organization_id = %s
                """,
                (resource_type_id, organization_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [col.name for col in cursor.description]

    return dict(zip(columns, row))


# ---------------------------------------------------------------------------
# Resource Batches
# ---------------------------------------------------------------------------


def create_resource_batch(
    organization_id: UUID,
    data: ResourceBatchCreate,
    user_id: UUID,
) -> dict:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            # 1. Verify resource type belongs to the authenticated organization
            cursor.execute(
                """
                SELECT id
                FROM resource_types
                WHERE id = %s AND organization_id = %s
                """,
                (data.resource_type_id, organization_id),
            )
            if cursor.fetchone() is None:
                raise ResourceTypeNotFoundError(
                    "Resource type not found or does not belong to organization"
                )

            # 2. Insert resource batch
            try:
                cursor.execute(
                    """
                    INSERT INTO resource_batches (
                        resource_type_id,
                        organization_id,
                        batch_code,
                        quantity,
                        source_description,
                        location
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, resource_type_id, organization_id, batch_code, quantity, source_description, received_at, location, created_at, updated_at
                    """,
                    (
                        data.resource_type_id,
                        organization_id,
                        data.batch_code,
                        data.quantity,
                        data.source_description,
                        data.location,
                    ),
                )
            except psycopg.errors.UniqueViolation:
                raise DuplicateBatchCodeError(
                    f"Batch code '{data.batch_code}' already exists in this organization"
                )

            batch_row = cursor.fetchone()
            columns = [col.name for col in cursor.description]
            batch_data = dict(zip(columns, batch_row))

            # 3. Atomically record initial RECEIVED event so inventory is tracked
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
                VALUES (%s, 'RECEIVED', %s, %s, %s, %s)
                """,
                (
                    batch_data["id"],
                    data.quantity,
                    data.location or "Default",
                    user_id,
                    "Initial batch receipt",
                ),
            )

        connection.commit()

    return batch_data


def list_resource_batches(organization_id: UUID) -> list[dict]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, resource_type_id, organization_id, batch_code, quantity, source_description, received_at, location, created_at, updated_at
                FROM resource_batches
                WHERE organization_id = %s
                ORDER BY created_at DESC
                """,
                (organization_id,),
            )
            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def get_resource_batch(organization_id: UUID, batch_id: UUID) -> dict | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, resource_type_id, organization_id, batch_code, quantity, source_description, received_at, location, created_at, updated_at
                FROM resource_batches
                WHERE id = %s AND organization_id = %s
                """,
                (batch_id, organization_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [col.name for col in cursor.description]

    return dict(zip(columns, row))


# ---------------------------------------------------------------------------
# Resource Events
# ---------------------------------------------------------------------------


def create_resource_event(
    organization_id: UUID,
    data: ResourceEventCreate,
    performed_by: UUID,
) -> dict:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            # 1. Verify resource batch belongs to caller's organization with row lock
            cursor.execute(
                """
                SELECT id
                FROM resource_batches
                WHERE id = %s AND organization_id = %s
                FOR UPDATE
                """,
                (data.resource_batch_id, organization_id),
            )
            if cursor.fetchone() is None:
                raise ResourceBatchNotFoundError(
                    "Resource batch not found or does not belong to organization"
                )

            # 2. If event reduces inventory, ensure sufficient stock to prevent negative inventory
            if data.event_type.value in ("TRANSFER_OUT", "DISTRIBUTED", "DAMAGED"):
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
                available = cursor.fetchone()[0]
                if available < data.quantity:
                    raise InsufficientInventoryError(
                        f"Insufficient inventory. Available: {available}, Requested: {data.quantity}"
                    )

            # 3. Insert event
            cursor.execute(
                """
                INSERT INTO resource_events (
                    resource_batch_id,
                    event_type,
                    quantity,
                    location,
                    performed_by,
                    reason,
                    transfer_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, resource_batch_id, event_type, quantity, location, performed_by, reason, transfer_id, created_at
                """,
                (
                    data.resource_batch_id,
                    data.event_type.value,
                    data.quantity,
                    data.location,
                    performed_by,
                    data.reason,
                    data.transfer_id,
                ),
            )
            row = cursor.fetchone()
            columns = [col.name for col in cursor.description]

        connection.commit()

    return dict(zip(columns, row))


def list_resource_events(
    organization_id: UUID,
    resource_batch_id: UUID | None = None,
) -> list[dict]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            if resource_batch_id is not None:
                # Ensure batch belongs to organization
                cursor.execute(
                    """
                    SELECT id
                    FROM resource_batches
                    WHERE id = %s AND organization_id = %s
                    """,
                    (resource_batch_id, organization_id),
                )
                if cursor.fetchone() is None:
                    raise ResourceBatchNotFoundError(
                        "Resource batch not found or does not belong to organization"
                    )

                cursor.execute(
                    """
                    SELECT e.id, e.resource_batch_id, e.event_type, e.quantity, e.location, e.performed_by, e.reason, e.transfer_id, e.created_at
                    FROM resource_events e
                    JOIN resource_batches b ON b.id = e.resource_batch_id
                    WHERE b.organization_id = %s AND e.resource_batch_id = %s
                    ORDER BY e.created_at DESC
                    """,
                    (organization_id, resource_batch_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT e.id, e.resource_batch_id, e.event_type, e.quantity, e.location, e.performed_by, e.reason, e.transfer_id, e.created_at
                    FROM resource_events e
                    JOIN resource_batches b ON b.id = e.resource_batch_id
                    WHERE b.organization_id = %s
                    ORDER BY e.created_at DESC
                    """,
                    (organization_id,),
                )

            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]


# ---------------------------------------------------------------------------
# Inventory Summary
# ---------------------------------------------------------------------------


def list_organization_inventory(organization_id: UUID) -> list[dict]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    b.id AS resource_batch_id,
                    b.batch_code,
                    b.resource_type_id,
                    rt.name AS resource_type_name,
                    rt.unit,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN e.event_type IN ('RECEIVED', 'TRANSFER_IN', 'ADJUSTED') THEN e.quantity
                                WHEN e.event_type IN ('TRANSFER_OUT', 'DISTRIBUTED', 'DAMAGED') THEN -e.quantity
                                ELSE 0
                            END
                        ),
                        0
                    ) AS available_quantity
                FROM resource_batches b
                JOIN resource_types rt ON rt.id = b.resource_type_id
                LEFT JOIN resource_events e ON e.resource_batch_id = b.id
                WHERE b.organization_id = %s
                GROUP BY b.id, b.batch_code, b.resource_type_id, rt.name, rt.unit, b.created_at
                ORDER BY b.created_at DESC
                """,
                (organization_id,),
            )
            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()

    return [
        {
            **dict(zip(columns, row)),
            "available_quantity": float(dict(zip(columns, row))["available_quantity"]),
        }
        for row in rows
    ]
