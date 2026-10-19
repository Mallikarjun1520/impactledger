from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.schemas import DistributionCreate
from app.infrastructure.database.distributions import create_distribution


class _MockContextManager:
    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def _distribution_data() -> DistributionCreate:
    return DistributionCreate(
        relief_event_id=uuid4(),
        resource_batch_id=uuid4(),
        quantity=5.0,
        destination="Clinic 1",
        beneficiary_count=2,
        notes=None,
    )


def test_db_create_distribution_cross_org_batch_rejection():
    org_id = uuid4()
    user_id = uuid4()

    data = _distribution_data()

    mock_cursor = MagicMock()

    # Batch lookup returns None because the batch does not belong
    # to the authenticated organization.
    mock_cursor.fetchone.return_value = None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)

    with patch(
        "psycopg.connect",
        return_value=_MockContextManager(mock_conn),
    ):
        with pytest.raises(
            ValueError,
            match="Resource batch not found or does not belong to organization",
        ):
            create_distribution(
                data,
                created_by=user_id,
                organization_id=org_id,
            )

    mock_conn.commit.assert_not_called()


def test_db_create_distribution_same_org_success():
    org_id = uuid4()
    user_id = uuid4()
    batch_id = uuid4()
    dist_id = uuid4()

    data = DistributionCreate(
        relief_event_id=uuid4(),
        resource_batch_id=batch_id,
        quantity=5.0,
        destination="Clinic 1",
        beneficiary_count=2,
        notes="Urgent",
    )

    mock_cursor = MagicMock()

    # 1. Batch lookup returns batch (with no linked PO / initiative).
    # 2. Inventory check returns available quantity.
    # 3. Relief event lookup returns the relief event id.
    # 4. Distribution insert returns distribution ID.
    mock_cursor.fetchone.side_effect = [
        (batch_id, None, None),
        (10.0,),
        (data.relief_event_id,),
        (dist_id,),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)
    audit_writer = MagicMock()

    with (
        patch("psycopg.connect", return_value=_MockContextManager(mock_conn)),
        patch(
            "app.infrastructure.database.distributions.insert_audit_event",
            audit_writer,
        ),
    ):
        result = create_distribution(
            data,
            created_by=user_id,
            organization_id=org_id,
        )

    assert result == str(dist_id)
    mock_conn.commit.assert_called_once()
    audit_writer.assert_called_once()
    assert audit_writer.call_args.kwargs["event_type"] == "ADMIN_ACTION"
    assert audit_writer.call_args.kwargs["details"]["action"] == "RESOURCE_DISTRIBUTED"


def test_db_create_distribution_distributed_event_carries_provenance():
    """The DISTRIBUTED event must inherit the batch's initiative and PO so the
    public transparency views attribute the distribution to the right
    initiative (regression for the omitted initiative_id bug)."""
    org_id = uuid4()
    user_id = uuid4()
    batch_id = uuid4()
    po_id = uuid4()
    initiative_id = uuid4()
    dist_id = uuid4()

    data = DistributionCreate(
        relief_event_id=uuid4(),
        resource_batch_id=batch_id,
        quantity=60.0,
        destination="Government Relief Camp, Kochi",
        beneficiary_count=120,
        notes=None,
    )

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (batch_id, po_id, initiative_id),
        (100.0,),
        (data.relief_event_id,),
        (dist_id,),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)
    audit_writer = MagicMock()

    with (
        patch("psycopg.connect", return_value=_MockContextManager(mock_conn)),
        patch(
            "app.infrastructure.database.distributions.insert_audit_event",
            audit_writer,
        ),
    ):
        result = create_distribution(
            data,
            created_by=user_id,
            organization_id=org_id,
        )

    assert result == str(dist_id)

    event_inserts = [
        call
        for call in mock_cursor.execute.call_args_list
        if "INSERT INTO resource_events" in call.args[0]
    ]
    assert len(event_inserts) == 1
    sql = event_inserts[0].args[0]
    params = event_inserts[0].args[1]
    assert "initiative_id" in sql
    assert "purchase_order_id" in sql
    assert params[:3] == (org_id, initiative_id, po_id)