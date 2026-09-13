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

    # 1. Batch lookup returns batch.
    # 2. Inventory check returns available quantity.
    # 3. Distribution insert returns distribution ID.
    mock_cursor.fetchone.side_effect = [
    (batch_id,),
    (10.0,),
    (data.relief_event_id,),
    (dist_id,),
]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)

    with patch(
        "psycopg.connect",
        return_value=_MockContextManager(mock_conn),
    ):
        result = create_distribution(
            data,
            created_by=user_id,
            organization_id=org_id,
        )

    assert result == str(dist_id)
    mock_conn.commit.assert_called_once()