"""Live PostgreSQL RLS tests for a local Supabase database.

Set IMPACTLEDGER_RLS_TEST_DATABASE_URL to the local port 54322 URL to run.
All fixture rows are created in one transaction and rolled back after each test.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict


@dataclass(frozen=True)
class RlsFixture:
    connection: psycopg.Connection
    organization_id: UUID
    other_organization_id: UUID
    initiative_id: UUID
    contribution_id: UUID
    other_contribution_id: UUID
    audit_event_id: UUID
    other_audit_event_id: UUID
    admin_id: UUID
    auditor_id: UUID
    member_id: UUID


@pytest.fixture
def rls_database() -> RlsFixture:
    dsn = os.environ.get("IMPACTLEDGER_RLS_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Set IMPACTLEDGER_RLS_TEST_DATABASE_URL to the local Supabase database URL")

    connection_info = conninfo_to_dict(dsn)
    if (
        connection_info.get("host") not in {"localhost", "127.0.0.1", "::1"}
        or connection_info.get("port") != "54322"
        or connection_info.get("dbname") != "postgres"
    ):
        pytest.fail(
            "RLS integration tests require the local postgres database on loopback port 54322"
        )

    connection = psycopg.connect(dsn)
    try:
        organization_id = uuid4()
        other_organization_id = uuid4()
        initiative_id = uuid4()
        contribution_id = uuid4()
        other_contribution_id = uuid4()
        audit_event_id = uuid4()
        other_audit_event_id = uuid4()
        admin_id, auditor_id, member_id, other_admin_id = (uuid4() for _ in range(4))
        fixture = RlsFixture(
            connection=connection,
            organization_id=organization_id,
            other_organization_id=other_organization_id,
            initiative_id=initiative_id,
            contribution_id=contribution_id,
            other_contribution_id=other_contribution_id,
            audit_event_id=audit_event_id,
            other_audit_event_id=other_audit_event_id,
            admin_id=admin_id,
            auditor_id=auditor_id,
            member_id=member_id,
        )

        connection.execute("BEGIN")
        connection.execute(
            """
            INSERT INTO organizations (id, name, slug)
            VALUES (%s, 'RLS integration org', %s),
                   (%s, 'RLS integration other org', %s)
            """,
            (
                organization_id,
                f"rls-test-{organization_id}",
                other_organization_id,
                f"rls-test-{other_organization_id}",
            ),
        )
        connection.execute(
            """
            INSERT INTO auth.users (
                id, aud, role, email, encrypted_password,
                raw_app_meta_data, raw_user_meta_data
            )
            VALUES
                (%s, 'authenticated', 'authenticated', %s, '', '{}'::jsonb, '{}'::jsonb),
                (%s, 'authenticated', 'authenticated', %s, '', '{}'::jsonb, '{}'::jsonb),
                (%s, 'authenticated', 'authenticated', %s, '', '{}'::jsonb, '{}'::jsonb),
                (%s, 'authenticated', 'authenticated', %s, '', '{}'::jsonb, '{}'::jsonb)
            """,
            (
                admin_id,
                f"{admin_id}@rls.integration.invalid",
                auditor_id,
                f"{auditor_id}@rls.integration.invalid",
                member_id,
                f"{member_id}@rls.integration.invalid",
                other_admin_id,
                f"{other_admin_id}@rls.integration.invalid",
            ),
        )
        connection.execute(
            """
            INSERT INTO organization_members (organization_id, user_id, role)
            VALUES (%s, %s, 'ADMIN'),
                   (%s, %s, 'AUDITOR'),
                   (%s, %s, 'VIEWER'),
                   (%s, %s, 'ADMIN')
            """,
            (
                organization_id,
                admin_id,
                organization_id,
                auditor_id,
                organization_id,
                member_id,
                other_organization_id,
                other_admin_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO initiatives (
                id, organization_id, name, slug, status
            )
            VALUES (%s, %s, 'RLS initiative', %s, 'ACTIVE')
            """,
            (initiative_id, organization_id, f"initiative-{initiative_id}"),
        )
        connection.execute(
            """
            INSERT INTO contributions (
                id, organization_id, initiative_id, restriction_scope,
                amount, status
            )
            VALUES (%s, %s, %s, 'INITIATIVE', 1, 'CONFIRMED'),
                   (%s, %s, NULL, 'UNRESTRICTED', 2, 'CONFIRMED')
            """,
            (
                contribution_id,
                organization_id,
                initiative_id,
                other_contribution_id,
                other_organization_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO audit_events (id, organization_id, event_type, details)
            VALUES (%s, %s, 'ADMIN_ACTION', '{"test":"local-rls"}'::jsonb),
                   (%s, %s, 'ADMIN_ACTION', '{"test":"cross-organization"}'::jsonb)
            """,
            (
                audit_event_id,
                organization_id,
                other_audit_event_id,
                other_organization_id,
            ),
        )
        yield fixture
    finally:
        connection.rollback()
        connection.close()


def _assume_identity(
    fixture: RlsFixture,
    role: str,
    user_id: UUID | None = None,
) -> None:
    fixture.connection.execute("RESET ROLE")
    fixture.connection.execute(
        "SELECT set_config('request.jwt.claim.sub', %s, true)",
        (str(user_id) if user_id else "",),
    )
    fixture.connection.execute(
        sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role))
    )


def _visible(fixture: RlsFixture, table: str, row_id: UUID) -> bool:
    if table not in {"contributions", "audit_events"}:
        raise ValueError(f"Unsupported RLS test table: {table}")
    return (
        fixture.connection.execute(
            sql.SQL("SELECT EXISTS (SELECT 1 FROM {} WHERE id = %s)").format(
                sql.Identifier(table)
            ),
            (row_id,),
        ).fetchone()[0]
        is True
    )


@pytest.mark.parametrize(
    ("role", "user_attribute"),
    [("ADMIN", "admin_id"), ("AUDITOR", "auditor_id")],
)
def test_privileged_member_can_read_organization_but_not_cross_organization_rows(
    rls_database: RlsFixture,
    role: str,
    user_attribute: str,
) -> None:
    user_id = getattr(rls_database, user_attribute)
    _assume_identity(rls_database, "authenticated", user_id)

    assert _visible(rls_database, "contributions", rls_database.contribution_id)
    assert _visible(rls_database, "audit_events", rls_database.audit_event_id)
    assert not _visible(rls_database, "contributions", rls_database.other_contribution_id)
    assert not _visible(rls_database, "audit_events", rls_database.other_audit_event_id)


def test_ordinary_member_can_read_organization_data_but_no_audit_events(
    rls_database: RlsFixture,
) -> None:
    _assume_identity(rls_database, "authenticated", rls_database.member_id)

    assert _visible(rls_database, "contributions", rls_database.contribution_id)
    assert not _visible(rls_database, "contributions", rls_database.other_contribution_id)
    assert not _visible(rls_database, "audit_events", rls_database.audit_event_id)
    assert not _visible(rls_database, "audit_events", rls_database.other_audit_event_id)


def test_unauthenticated_role_cannot_read_raw_rows_but_can_read_public_projection(
    rls_database: RlsFixture,
) -> None:
    _assume_identity(rls_database, "anon")

    assert rls_database.connection.execute("SELECT auth.uid()").fetchone()[0] is None
    assert not _visible(rls_database, "contributions", rls_database.contribution_id)
    assert not _visible(rls_database, "audit_events", rls_database.audit_event_id)
    assert (
        rls_database.connection.execute(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM public_initiative_summary
                 WHERE initiative_id = %s
            )
            """,
            (rls_database.initiative_id,),
        ).fetchone()[0]
        is True
    )


def test_admin_from_another_organization_cannot_read_foreign_audit_events(
    rls_database: RlsFixture,
) -> None:
    other_admin_id = rls_database.connection.execute(
        """
        SELECT user_id
          FROM organization_members
         WHERE organization_id = %s AND role = 'ADMIN'
        """,
        (rls_database.other_organization_id,),
    ).fetchone()[0]
    _assume_identity(rls_database, "authenticated", other_admin_id)

    assert _visible(rls_database, "audit_events", rls_database.other_audit_event_id)
    assert not _visible(rls_database, "audit_events", rls_database.audit_event_id)
    assert not _visible(rls_database, "contributions", rls_database.contribution_id)
