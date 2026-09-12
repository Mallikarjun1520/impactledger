from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.core.config import settings
from app.api.v1.schemas import OrganizationMemberCreate
from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.api.v1.schemas import OrganizationMemberCreate, OrganizationRole
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
def list_organization_members(
    organization_id: UUID,
) -> list[OrganizationMembership]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT organization_id, user_id, role::text
                FROM organization_members
                WHERE organization_id = %s
                ORDER BY created_at
                """,
                (organization_id,),
            )

            rows = cursor.fetchall()

    return [
        OrganizationMembership(
            organization_id=row[0],
            user_id=row[1],
            role=row[2],
        )
        for row in rows
    ]
def add_organization_member(
    organization_id: UUID,
    data: OrganizationMemberCreate,
) -> OrganizationMembership:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            # Make sure the target organization exists
            cursor.execute(
                """
                SELECT id
                FROM organizations
                WHERE id = %s
                """,
                (organization_id,),
            )

            if cursor.fetchone() is None:
                raise ValueError("Organization not found")

            # Make sure the target user exists
            cursor.execute(
                """
                SELECT id
                FROM auth.users
                WHERE id = %s
                """,
                (data.user_id,),
            )

            if cursor.fetchone() is None:
                raise ValueError("User not found")

            # Add the membership
            cursor.execute(
                """
                INSERT INTO organization_members (
                    organization_id,
                    user_id,
                    role
                )
                VALUES (%s, %s, %s)
                RETURNING organization_id, user_id, role::text
                """,
                (
                    organization_id,
                    data.user_id,
                    data.role.value,
                ),
            )

            row = cursor.fetchone()

            if row is None:
                raise RuntimeError("Failed to create organization membership")

            return OrganizationMembership(
                organization_id=row[0],
                user_id=row[1],
                role=row[2],
            )
def update_organization_member(
    organization_id: UUID,
    user_id: UUID,
    role: OrganizationRole,
) -> OrganizationMembership | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE organization_members
                SET role = %s,
                    updated_at = NOW()
                WHERE organization_id = %s
                  AND user_id = %s
                RETURNING organization_id, user_id, role::text
                """,
                (
                    role.value,
                    organization_id,
                    user_id,
                ),
            )

            row = cursor.fetchone()

    if row is None:
        return None

    return OrganizationMembership(
        organization_id=row[0],
        user_id=row[1],
        role=row[2],
    )