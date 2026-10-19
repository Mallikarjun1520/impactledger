from uuid import UUID

import psycopg

from app.api.v1.schemas import ContributionCreate
from app.core.config import settings
from app.infrastructure.database.audit_logs import insert_audit_event


def create_contribution(
    organization_id: UUID,
    data: ContributionCreate,
    user_id: UUID,
) -> dict:
    contributor_id = data.contributor_user_id or user_id

    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO contributions (
                    organization_id,
                    contributor_user_id,
                    amount,
                    currency,
                    visibility,
                    status,
                    received_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, organization_id, contributor_user_id, amount, currency, visibility, status, received_at, created_at
                """,
                (
                    organization_id,
                    contributor_id,
                    data.amount,
                    data.currency,
                    data.visibility.value,
                    data.status.value,
                    data.received_at,
                ),
            )
            row = cursor.fetchone()
            columns = [col.name for col in cursor.description]
            contribution = dict(zip(columns, row))
            insert_audit_event(
                cursor,
                organization_id=organization_id,
                event_type="ADMIN_ACTION",
                user_id=user_id,
                details={
                    "action": "CONTRIBUTION_RECORDED",
                    "entity_type": "contribution",
                    "entity_id": str(contribution["id"]),
                    "amount": str(data.amount),
                    "currency": data.currency,
                },
            )

        connection.commit()

    return contribution


def list_contributions(organization_id: UUID) -> list[dict]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, organization_id, contributor_user_id, amount, currency, visibility, status, received_at, created_at
                FROM contributions
                WHERE organization_id = %s
                ORDER BY created_at DESC
                """,
                (organization_id,),
            )
            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def get_contribution(organization_id: UUID, contribution_id: UUID) -> dict | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, organization_id, contributor_user_id, amount, currency, visibility, status, received_at, created_at
                FROM contributions
                WHERE id = %s AND organization_id = %s
                """,
                (contribution_id, organization_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [col.name for col in cursor.description]

    return dict(zip(columns, row))
