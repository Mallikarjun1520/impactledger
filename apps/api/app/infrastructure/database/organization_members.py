from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.api.v1.schemas import OrganizationMemberCreate, OrganizationRole
from app.core.config import settings
from app.core.exceptions import (
    LastAdminError,
    MemberAlreadyExistsError,
    OrganizationNotFoundError,
)
from app.infrastructure.database.audit_logs import insert_audit_event


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
    actor_user_id: UUID | None = None,
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
                raise OrganizationNotFoundError("Organization not found")

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
            try:
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
            except psycopg.errors.UniqueViolation:
                raise MemberAlreadyExistsError("User is already a member of this organization")

            row = cursor.fetchone()

            if row is None:
                raise RuntimeError("Failed to create organization membership")

            if actor_user_id is not None:
                insert_audit_event(
                    cursor,
                    organization_id=organization_id,
                    event_type="MEMBER_ADDED",
                    user_id=actor_user_id,
                    subject_user_id=data.user_id,
                    details={
                        "entity_type": "organization_member",
                        "entity_id": str(data.user_id),
                        "role": row[2],
                    },
                )

            return OrganizationMembership(
                organization_id=row[0],
                user_id=row[1],
                role=row[2],
            )


def update_organization_member(
    organization_id: UUID,
    user_id: UUID,
    role: OrganizationRole,
    actor_user_id: UUID | None = None,
) -> OrganizationMembership | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            # Lock the organization row to serialize member role/removal operations
            cursor.execute(
                """
                SELECT id
                FROM organizations
                WHERE id = %s
                FOR UPDATE
                """,
                (organization_id,),
            )

            if cursor.fetchone() is None:
                raise OrganizationNotFoundError("Organization not found")

            # Check target member's current role with row-level lock
            cursor.execute(
                """
                SELECT role::text
                FROM organization_members
                WHERE organization_id = %s
                  AND user_id = %s
                FOR UPDATE
                """,
                (organization_id, user_id),
            )
            current_member = cursor.fetchone()

            if current_member is None:
                return None

            current_role = current_member[0]

            # Last-admin protection: cannot demote the final ADMIN
            if current_role == "ADMIN" and role.value != "ADMIN":
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM organization_members
                    WHERE organization_id = %s
                      AND role = 'ADMIN'
                    """,
                    (organization_id,),
                )
                admin_count = cursor.fetchone()[0]
                if admin_count <= 1:
                    raise LastAdminError("Organization must have at least one admin")

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

            if actor_user_id is not None and row is not None and current_role != row[2]:
                insert_audit_event(
                    cursor,
                    organization_id=organization_id,
                    event_type="MEMBER_ROLE_CHANGED",
                    user_id=actor_user_id,
                    subject_user_id=user_id,
                    details={
                        "entity_type": "organization_member",
                        "entity_id": str(user_id),
                        "old_role": current_role,
                        "new_role": row[2],
                    },
                )

    if row is None:
        return None

    return OrganizationMembership(
        organization_id=row[0],
        user_id=row[1],
        role=row[2],
    )


def delete_organization_member(
    organization_id: UUID,
    user_id: UUID,
    actor_user_id: UUID | None = None,
) -> bool:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            # Lock the organization row to serialize member role/removal operations
            cursor.execute(
                """
                SELECT id
                FROM organizations
                WHERE id = %s
                FOR UPDATE
                """,
                (organization_id,),
            )

            if cursor.fetchone() is None:
                raise OrganizationNotFoundError("Organization not found")

            # Check target member's current role with row-level lock
            cursor.execute(
                """
                SELECT role::text
                FROM organization_members
                WHERE organization_id = %s
                  AND user_id = %s
                FOR UPDATE
                """,
                (organization_id, user_id),
            )
            current_member = cursor.fetchone()

            if current_member is None:
                return False

            current_role = current_member[0]

            # Last-admin protection: cannot delete the final ADMIN
            if current_role == "ADMIN":
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM organization_members
                    WHERE organization_id = %s
                      AND role = 'ADMIN'
                    """,
                    (organization_id,),
                )
                admin_count = cursor.fetchone()[0]
                if admin_count <= 1:
                    raise LastAdminError("Organization must have at least one admin")

            cursor.execute(
                """
                DELETE FROM organization_members
                WHERE organization_id = %s
                  AND user_id = %s
                """,
                (organization_id, user_id),
            )
            if actor_user_id is not None:
                insert_audit_event(
                    cursor,
                    organization_id=organization_id,
                    event_type="MEMBER_REMOVED",
                    user_id=actor_user_id,
                    subject_user_id=user_id,
                    details={
                        "entity_type": "organization_member",
                        "entity_id": str(user_id),
                        "role": current_role,
                    },
                )
            return True