"""Tests for the unauthenticated public transparency endpoints.

These tests guard the regression that produced
``psycopg.errors.UndefinedTable: relation "public_initiative_summary" does not
exist``: a missing projection view (or a database outage) must surface as an
explicit service error, never as an empty (zero) dataset, and the client must
never see SQL text.
"""
import inspect
from unittest.mock import MagicMock, patch
from uuid import uuid4

import psycopg
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.v1 import public as public_api
from app.main import app

client = TestClient(app)

ORGANIZATION_SLUG = "demo-relief"
INITIATIVE_SLUG = "flood-relief-2026"


def test_public_routes_are_mounted():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/public/organizations/{org_slug}/initiatives" in paths
    assert (
        "/api/v1/public/organizations/{org_slug}/initiatives/{initiative_slug}"
        in paths
    )
    assert "/api/v1/public/anchors/{batch_id}" in paths


def test_list_initiatives_reads_the_sanitized_summary_view(monkeypatch):
    rows = [{"org_slug": ORGANIZATION_SLUG, "initiative_slug": INITIATIVE_SLUG}]
    reader = MagicMock(return_value=rows)
    monkeypatch.setattr(public_api, "_rows", reader)

    response = client.get(f"/api/v1/public/organizations/{ORGANIZATION_SLUG}/initiatives")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == rows
    sql = reader.call_args.args[0]
    assert "public_initiative_summary" in sql
    assert reader.call_args.args[1] == (ORGANIZATION_SLUG,)


def test_list_initiatives_returns_empty_list_for_unknown_org(monkeypatch):
    reader = MagicMock(return_value=[])
    monkeypatch.setattr(public_api, "_rows", reader)

    response = client.get("/api/v1/public/organizations/does-not-exist/initiatives")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_detail_returns_summary_and_sanitized_sections(monkeypatch):
    initiative_id = uuid4()
    summary = {
        "initiative_id": initiative_id,
        "org_slug": ORGANIZATION_SLUG,
        "org_name": "Demo Relief Foundation",
        "initiative_slug": INITIATIVE_SLUG,
        "initiative_name": "Flood Relief 2026",
        "description": None,
        "category": "shelter",
        "status": "ACTIVE",
        "contribution_count": 0,
        "contribution_total": "0",
        "allocated_total": "0",
        "paid_total": "0",
        "unallocated_total": "0",
        "allocation_pct": "0",
    }
    reader = MagicMock(
        side_effect=[
            [summary],
            [{"initiative_id": initiative_id, "resource_name": "Blankets", "unit": "unit"}],
            [],
            [],
        ]
    )
    monkeypatch.setattr(public_api, "_rows", reader)

    response = client.get(
        f"/api/v1/public/organizations/{ORGANIZATION_SLUG}/initiatives/{INITIATIVE_SLUG}"
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["summary"]["initiative_slug"] == INITIATIVE_SLUG
    assert body["summary"]["contribution_total"] == "0"
    assert len(body["resources"]) == 1
    assert body["reconciliation_flags"] == []
    assert body["anchor_batches"] == []

    queries = [call.args[0] for call in reader.call_args_list]
    assert "public_initiative_summary" in queries[0]
    assert "public_initiative_resources" in queries[1]
    assert "public_reconciliation_flags" in queries[2]
    assert "public_anchor_batches" in queries[3]
    # Each subsequent lookup is scoped by the resolved initiative id.
    assert reader.call_args_list[1].args[1] == (initiative_id,)


def test_detail_missing_initiative_returns_404(monkeypatch):
    reader = MagicMock(return_value=[])
    monkeypatch.setattr(public_api, "_rows", reader)

    response = client.get(
        "/api/v1/public/organizations/demo-relief/initiatives/unknown"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_anchor_missing_returns_404(monkeypatch):
    reader = MagicMock(return_value=[])
    monkeypatch.setattr(public_api, "_rows", reader)

    response = client.get(f"/api/v1/public/anchors/{uuid4()}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "error",
    [
        psycopg.errors.UndefinedTable('relation "public_initiative_summary" does not exist'),
        psycopg.OperationalError("could not connect to server"),
    ],
)
def test_database_failure_is_503_and_never_leaks_sql(error):
    with patch.object(public_api.psycopg, "connect", side_effect=error):
        response = client.get(f"/api/v1/public/organizations/{ORGANIZATION_SLUG}/initiatives")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == (
        "Public transparency data is temporarily unavailable"
    )
    body = response.text
    assert "public_initiative_summary" not in body
    assert "does not exist" not in body
    assert "could not connect" not in body
    assert "SELECT" not in body.upper()


def test_database_failure_is_logged(caplog):
    error = psycopg.errors.UndefinedTable('relation "public_initiative_summary" does not exist')
    with (
        caplog.at_level("ERROR", logger=public_api.logger.name),
        patch.object(public_api.psycopg, "connect", side_effect=error),
    ):
        response = client.get(
            f"/api/v1/public/organizations/{ORGANIZATION_SLUG}/initiatives"
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Public transparency query failed" in caplog.text


def test_public_module_never_selects_from_private_projection_tables():
    source = inspect.getsource(public_api)
    for allowed in ("public_initiative_summary", "public_initiative_resources",
                    "public_reconciliation_flags", "public_anchor_batches"):
        assert allowed in source
    # The public surface must not read the raw financial tables directly.
    for forbidden in (
        "FROM contributions",
        "FROM allocations",
        "FROM payments",
        "FROM commitments",
        "FROM purchase_orders",
        "FROM audit_events",
        "FROM evidence",
    ):
        assert forbidden not in source
