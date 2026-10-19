"""Tests for the local Flood Relief 2026 demo seed.

Static tests assert the shape and safety guarantees of
``supabase/demo_flood_relief.sql`` (idempotency, initiative attribution, and
that it never fabricates ``auth.users`` / ``domain_events`` / ``anchor_batches``).

The integration test is opt-in: it executes the script (twice) against a real
local Supabase Postgres and asserts idempotency plus the public projection
totals. It is skipped unless ``IMPACTLEDGER_DEMO_SEED_TEST_DATABASE_URL`` names
the local loopback database on port 54322.
"""
from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_SEED = REPO_ROOT / "supabase" / "demo_flood_relief.sql"


# ---------------------------------------------------------------------------
# Static contract of the seed script
# ---------------------------------------------------------------------------


def _seed_text() -> str:
    assert DEMO_SEED.is_file(), f"missing {DEMO_SEED}"
    return DEMO_SEED.read_text(encoding="utf-8")


def test_demo_seed_targets_the_canonical_demo_tenant():
    sql = _seed_text()
    assert "'demo-relief'" in sql
    assert "'flood-relief-2026'" in sql


def test_demo_seed_is_idempotent():
    sql = _seed_text()
    # Every entity is guarded by a lookup / existence check before insert.
    assert "IF NOT EXISTS" in sql
    assert "RETURNING id INTO" in sql
    assert "DO $$" in sql


def test_demo_seed_never_fabricates_privileged_records():
    sql = _seed_text()
    # No fabricated identities, provenance, or on-chain proofs. (The script
    # may *read* organization_members to resolve an actor, and may name these
    # tables in comments, but it must never insert into them.)
    assert "INSERT INTO auth.users" not in sql
    assert "INSERT INTO organization_members" not in sql
    assert "INSERT INTO domain_events" not in sql
    assert "INSERT INTO anchor_batches" not in sql
    assert "INSERT INTO evidence" not in sql


def test_demo_seed_links_contribution_and_allocation_to_initiative():
    sql = _seed_text()
    assert "restriction_scope" in sql and "'INITIATIVE'" in sql
    assert "initiative_id" in sql
    # Illustrative amounts.
    assert "50000" in sql  # contribution
    assert "30000" in sql  # allocation
    assert "25000" in sql  # commitment + PO + payment


def test_demo_seed_attributes_resource_events_to_initiative():
    sql = _seed_text()
    assert "'RECEIVED'" in sql
    assert "'DISTRIBUTED'" in sql
    # The resource_events inserts carry initiative_id + purchase_order_id.
    assert "initiative_id, purchase_order_id, resource_batch_id" in sql
    assert "DEMO-FR2026-BLANKETS-001" in sql


def test_demo_seed_records_a_named_distribution():
    sql = _seed_text()
    assert "'Government Relief Camp, Kochi'" in sql
    assert "'Flood Relief 2026 - Blanket Distribution'" in sql


# ---------------------------------------------------------------------------
# Opt-in live idempotency / projection test
# ---------------------------------------------------------------------------


@pytest.fixture
def live_demo_seed(monkeypatch: pytest.MonkeyPatch):
    dsn = os.environ.get("IMPACTLEDGER_DEMO_SEED_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip(
            "Set IMPACTLEDGER_DEMO_SEED_TEST_DATABASE_URL to local Supabase PostgreSQL"
        )

    database = conninfo_to_dict(dsn)
    if (
        database.get("host") not in {"localhost", "127.0.0.1", "::1"}
        or database.get("port") != "54322"
        or database.get("dbname") != "postgres"
    ):
        pytest.fail(
            "Demo seed tests require the local postgres database on loopback port 54322"
        )

    connection = psycopg.connect(dsn)
    connection.execute("BEGIN")

    connection.execute(
        """
        INSERT INTO organizations (name, slug, lifecycle)
        VALUES ('Demo Relief Foundation', 'demo-relief', 'ACTIVE')
        ON CONFLICT (slug) DO NOTHING
        """
    )
    org_row = connection.execute(
        "SELECT id FROM organizations WHERE slug = 'demo-relief'"
    ).fetchone()
    organization_id = org_row[0]

    connection.execute(
        """
        INSERT INTO initiatives (organization_id, name, slug, category, status)
        VALUES (%s, 'Flood Relief 2026', 'flood-relief-2026', 'shelter', 'ACTIVE')
        ON CONFLICT (organization_id, slug) DO NOTHING
        """,
        (organization_id,),
    )
    initiative_row = connection.execute(
        "SELECT id FROM initiatives WHERE organization_id = %s AND slug = 'flood-relief-2026'",
        (organization_id,),
    ).fetchone()
    initiative_id = initiative_row[0]

    # A real local user is required for purchase_orders.approved_by.
    user_id = uuid4()
    connection.execute(
        """
        INSERT INTO auth.users (
            id, aud, role, email, encrypted_password,
            raw_app_meta_data, raw_user_meta_data
        )
        VALUES (%s, 'authenticated', 'authenticated', %s, '', '{}'::jsonb, '{}'::jsonb)
        """,
        (user_id, f"{user_id}@demo.seed.invalid"),
    )
    connection.execute(
        """
        INSERT INTO organization_members (organization_id, user_id, role)
        VALUES (%s, %s, 'ADMIN')
        ON CONFLICT (organization_id, user_id) DO NOTHING
        """,
        (organization_id, user_id),
    )

    yield {
        "connection": connection,
        "organization_id": organization_id,
        "initiative_id": initiative_id,
    }

    connection.rollback()
    connection.close()


def test_demo_seed_is_repeatable_and_populates_public_views(live_demo_seed):
    connection = live_demo_seed["connection"]
    initiative_id = live_demo_seed["initiative_id"]

    sql = _seed_text().encode("utf-8")

    for _ in range(2):
        result = connection.pgconn.exec_(sql)
        assert result.status == psycopg.pq.ExecStatus.COMMAND_OK, result.error_message

    summary = connection.execute(
        """
        SELECT contribution_count, contribution_total, allocated_total, paid_total
          FROM public_initiative_summary
         WHERE initiative_id = %s
        """,
        (initiative_id,),
    ).fetchone()
    assert summary is not None
    assert summary[0] == 1
    assert summary[1] == Decimal("50000.00")
    assert summary[2] == Decimal("30000.00")
    assert summary[3] == Decimal("25000.00")

    resources = connection.execute(
        """
        SELECT received, distributed
          FROM public_initiative_resources
         WHERE initiative_id = %s AND resource_name = 'Blankets'
        """,
        (initiative_id,),
    ).fetchone()
    assert resources == (Decimal("100.000"), Decimal("60.000"))

    assert initiative_id is not None
    distributed = connection.execute(
        """
        SELECT purchase_order_id
          FROM resource_events
         WHERE event_type = 'DISTRIBUTED'
           AND initiative_id = %s
        """,
        (initiative_id,),
    ).fetchone()
    assert distributed is not None
    assert distributed[0] is not None
