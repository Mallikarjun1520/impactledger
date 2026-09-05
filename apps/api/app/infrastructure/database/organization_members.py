from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.core.config import settings


@dataclass(frozen=True)
class OrganizationMembership:
    organization_id: UUID
    user_id: UUID
    role: str


def get_organization_membership(
    user_id: UUID,
    organization_id: UUID,
) -> OrganizationMembership | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT organization_id, user_id, role::text
                FROM organization_members
                WHERE user_id = %s
                  AND organization_id = %s
                """,
                (user_id, organization_id),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return OrganizationMembership(
        organization_id=row[0],
        user_id=row[1],
        role=row[2],
    )
