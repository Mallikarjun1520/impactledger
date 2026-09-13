from uuid import UUID

import psycopg

from app.api.v1.schemas import OrganizationCreate
from app.core.config import settings
from app.core.exceptions import DuplicateSlugError


def create_organization(
    data: OrganizationCreate,
    user_id: UUID,
) -> dict:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO organizations (
                        name,
                        slug,
                        description
                    )
                    VALUES (%s, %s, %s)
                    RETURNING id, name, slug, description
                    """,
                    (
                        data.name,
                        data.slug,
                        data.description,
                    ),
                )
            except psycopg.errors.UniqueViolation:
                raise DuplicateSlugError(f"Organization with slug '{data.slug}' already exists")

            organization = cursor.fetchone()

            if organization is None:
                raise ValueError("Failed to create organization")

            organization_id, name, slug, description = organization

            cursor.execute(
                """
                INSERT INTO organization_members (
                    organization_id,
                    user_id,
                    role
                )
                VALUES (%s, %s, 'ADMIN')
                """,
                (
                    organization_id,
                    user_id,
                ),
            )

            return {
                "id": organization_id,
                "name": name,
                "slug": slug,
                "description": description,
            }


def get_organization(
    organization_id: UUID,
) -> dict | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, slug, description, created_at, updated_at
                FROM organizations
                WHERE id = %s
                """,
                (organization_id,),
            )

            organization = cursor.fetchone()

            if organization is None:
                return None

            columns = [column.name for column in cursor.description]

            return dict(zip(columns, organization))