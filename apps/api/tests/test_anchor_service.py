from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1 import anchor as anchor_api
from app.core import authorization as authorization_module
from app.core.auth import get_current_user
from app.infrastructure.database.anchor import AnchorBatchRow
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app
from app.services import anchor_service

client = TestClient(app)


def _batch(status="PENDING", tx_hash=None):
    return AnchorBatchRow(
        id=uuid4(),
        organization_id=uuid4(),
        merkle_root="a" * 64,
        event_count=1,
        chain_id=84532,
        contract_address="0xcontract",
        tx_hash=tx_hash,
        block_number=42 if tx_hash else None,
        status=status,
        submitted_at=None,
        confirmed_at=None,
        failure_reason=None,
        created_at=datetime.now(UTC),
    )


def test_close_and_submit_creates_batch_and_submits_its_root():
    batch = _batch()
    adapter = MagicMock()
    adapter.submit.return_value = MagicMock(
        tx_hash="0xtx",
        block_number=42,
        contract_address="0xcontract",
    )
    submitted = _batch(status="SUBMITTED", tx_hash="0xtx")

    with (
        patch.object(anchor_service.anchor_db, "create_batch", return_value=batch) as create,
        patch.object(anchor_service, "build_adapter", return_value=adapter),
        patch.object(anchor_service.anchor_db, "record_submission"),
        patch.object(anchor_service.anchor_db, "get_batch", return_value=submitted),
    ):
        result = anchor_service.close_and_submit_batch(
            organization_id=batch.organization_id,
            contract_address="0xcontract",
            chain_id=84532,
            max_events=50,
        )

    assert result is submitted
    assert create.call_args.kwargs["max_events"] == 50
    assert create.call_args.kwargs["merkle_root"] is not None
    adapter.submit.assert_called_once()


def test_submission_failure_preserves_failed_batch_for_retry():
    batch = _batch()
    adapter = MagicMock()
    adapter.submit.side_effect = RuntimeError("provider unavailable")

    with (
        patch.object(anchor_service.anchor_db, "create_batch", return_value=batch),
        patch.object(anchor_service, "build_adapter", return_value=adapter),
        patch.object(anchor_service.anchor_db, "mark_failed") as mark_failed,
        patch.object(anchor_service, "create_audit_event") as audit_event,
    ):
        result = anchor_service.close_and_submit_batch(
            organization_id=batch.organization_id,
            contract_address="0xcontract",
            chain_id=84532,
            max_events=50,
        )

    assert result is None
    mark_failed.assert_called_once_with(batch.id, "provider unavailable")
    audit_event.assert_called_once()


def test_confirmation_marks_batch_after_adapter_confirms():
    batch = _batch(status="SUBMITTED", tx_hash="0xtx")
    adapter = MagicMock()
    adapter.confirmed.return_value = True

    with (
        patch.object(anchor_service.anchor_db, "get_batch", return_value=batch),
        patch.object(anchor_service, "build_adapter", return_value=adapter),
        patch.object(anchor_service.anchor_db, "mark_confirmed") as mark_confirmed,
    ):
        assert anchor_service.confirm_batch(batch.id, min_confirmations=3)

    mark_confirmed.assert_called_once_with(batch.id, 42)


def test_confirmation_waits_without_changing_batch():
    batch = _batch(status="SUBMITTED", tx_hash="0xtx")
    adapter = MagicMock()
    adapter.confirmed.return_value = False

    with (
        patch.object(anchor_service.anchor_db, "get_batch", return_value=batch),
        patch.object(anchor_service, "build_adapter", return_value=adapter),
        patch.object(anchor_service.anchor_db, "mark_confirmed") as mark_confirmed,
    ):
        assert not anchor_service.confirm_batch(batch.id, min_confirmations=3)

    mark_confirmed.assert_not_called()


def test_viewer_cannot_confirm_an_anchor_batch(monkeypatch):
    user_id = uuid4()
    org_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: (
            OrganizationMembership(org_id, user_id, "VIEWER")
            if current_user_id == user_id and current_org_id == org_id
            else None
        ),
    )

    try:
        with patch.object(anchor_api.anchor_service, "confirm_batch") as confirm:
            response = client.post(
                f"/api/v1/organizations/{org_id}/anchor/batches/{uuid4()}/confirm",
                headers={"X-Organization-ID": str(org_id)},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    confirm.assert_not_called()


def test_cannot_confirm_another_organizations_batch(monkeypatch):
    user_id = uuid4()
    org_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: (
            OrganizationMembership(org_id, user_id, "ADMIN")
            if current_user_id == user_id and current_org_id == org_id
            else None
        ),
    )

    try:
        with (
            patch.object(anchor_api.anchor_db, "get_batch", return_value=_batch()),
            patch.object(anchor_api.anchor_service, "confirm_batch") as confirm,
        ):
            response = client.post(
                f"/api/v1/organizations/{org_id}/anchor/batches/{uuid4()}/confirm",
                headers={"X-Organization-ID": str(org_id)},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    confirm.assert_not_called()
