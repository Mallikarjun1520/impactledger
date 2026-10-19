from datetime import datetime
from uuid import UUID

import psycopg
from psycopg import Cursor
from psycopg.types.json import Jsonb

from app.core.config import settings


def insert_audit_event(
    cursor: Cursor,
    organization_id: UUID,
    event_type: str,
    user_id: UUID | None = None,
    subject_user_id: UUID | None = None,
    details: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    cursor.execute(
        """
        INSERT INTO audit_events (
            organization_id, event_type, user_id, subject_user_id,
            ip, user_agent, details
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, organization_id, event_type::text AS event_type, user_id,
                  subject_user_id, ip::text AS ip, user_agent, details, created_at
        """,
        (
            organization_id,
            event_type,
            user_id,
            subject_user_id,
            ip,
            user_agent,
            Jsonb(details or {}),
        ),
    )
    row = cursor.fetchone()
    columns = [column.name for column in cursor.description]
    return dict(zip(columns, row, strict=False))


def create_audit_event(
    organization_id: UUID,
    event_type: str,
    user_id: UUID | None = None,
    subject_user_id: UUID | None = None,
    details: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            return insert_audit_event(
                cursor,
                organization_id=organization_id,
                event_type=event_type,
                user_id=user_id,
                subject_user_id=subject_user_id,
                details=details,
                ip=ip,
                user_agent=user_agent,
            )


def create_audit_log(
    organization_id: UUID,
    actor_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    metadata: dict | None = None,
) -> dict:
    """Compatibility writer for legacy callers, stored as ADMIN_ACTION."""
    return create_audit_event(
        organization_id=organization_id,
        event_type="ADMIN_ACTION",
        user_id=actor_id,
        details={
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "metadata": metadata or {},
        },
    )


def list_audit_logs(
    organization_id: UUID,
    action: str | None = None,
    entity_type: str | None = None,
    actor_id: UUID | None = None,
    entity_id: UUID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = ["organization_id = %s"]
    params: list = [organization_id]

    if action is not None:
        conditions.append("(event_type::text = %s OR details->>'action' = %s)")
        params.extend([action, action])

    if entity_type is not None:
        conditions.append("details->>'entity_type' = %s")
        params.append(entity_type)

    if actor_id is not None:
        conditions.append("user_id = %s")
        params.append(actor_id)

    if entity_id is not None:
        conditions.append("details->>'entity_id' = %s")
        params.append(str(entity_id))

    if start is not None:
        conditions.append("created_at >= %s")
        params.append(start)

    if end is not None:
        conditions.append("created_at <= %s")
        params.append(end)

    where_clause = " AND ".join(conditions)
    params.extend([limit, offset])

    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, organization_id, event_type::text AS event_type,
                       user_id, subject_user_id, ip::text AS ip, user_agent,
                       details, created_at
                FROM audit_events
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()

    return [dict(zip(columns, row, strict=False)) for row in rows]
