from contextlib import nullcontext
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.infrastructure.database import anchor


def _mock_database(rows, merkle_root="abc123"):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = (
        uuid4(),
        uuid4(),
        merkle_root,
        len(rows),
        84532,
        None,
        None,
        None,
        "PENDING",
        None,
        None,
        None,
        datetime.now(UTC),
    )
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.transaction.return_value = nullcontext()
    return cursor, connection


def test_create_batch_locks_events_and_persists_immutable_items():
    event_id = uuid4()
    cursor, connection = _mock_database([(event_id, "a" * 64, 1)], "b" * 64)

    with patch("psycopg.connect", return_value=nullcontext(connection)):
        batch = anchor.create_batch(
            organization_id=uuid4(),
            max_events=10,
            chain_id=84532,
            contract_address=None,
            merkle_root=lambda hashes: "b" * 64,
        )

    assert batch is not None
    assert batch.merkle_root == "b" * 64
    select_sql = cursor.execute.call_args_list[0].args[0]
    assert "FOR UPDATE OF e SKIP LOCKED" in select_sql
    assert "batch.status <> 'FAILED'" in select_sql
    executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
    assert "INSERT INTO anchor_batch_items" in executed_sql
    assert "UPDATE domain_events" not in executed_sql
    assert "DELETE FROM domain_events" not in executed_sql


def test_create_batch_returns_none_when_no_unbatched_events():
    cursor, connection = _mock_database([])

    with patch("psycopg.connect", return_value=nullcontext(connection)):
        batch = anchor.create_batch(
            organization_id=uuid4(),
            max_events=10,
            chain_id=84532,
            contract_address=None,
            merkle_root=lambda hashes: "b" * 64,
        )

    assert batch is None
    assert cursor.execute.call_count == 1


def test_failed_batch_items_are_preserved_and_eligible_for_new_batch():
    event_id = uuid4()
    cursor1, connection1 = _mock_database([(event_id, "a" * 64, 1)], "b" * 64)
    failed_cursor, failed_connection = _mock_database([])
    cursor2, connection2 = _mock_database([(event_id, "a" * 64, 1)], "c" * 64)
    connect = [
        nullcontext(connection1),
        nullcontext(failed_connection),
        nullcontext(connection2),
    ]

    with patch("psycopg.connect", side_effect=connect):
        first = anchor.create_batch(
            organization_id=uuid4(),
            max_events=10,
            chain_id=84532,
            contract_address=None,
            merkle_root=lambda hashes: "b" * 64,
        )
        anchor.mark_failed(first.id, "temporary provider failure")
        second = anchor.create_batch(
            organization_id=uuid4(),
            max_events=10,
            chain_id=84532,
            contract_address=None,
            merkle_root=lambda hashes: "c" * 64,
        )

    assert first is not None
    assert second is not None
    assert first.id != second.id
    assert first.merkle_root != second.merkle_root
    for cursor in (cursor1, cursor2):
        statements = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        assert "INSERT INTO anchor_batch_items" in statements
        assert "UPDATE domain_events" not in statements
        assert "DELETE FROM anchor_batch_items" not in statements
    failed_statements = "\n".join(
        call.args[0] for call in failed_cursor.execute.call_args_list
    )
    assert "UPDATE anchor_batches" in failed_statements
    assert "UPDATE domain_events" not in failed_statements


def test_confirmation_updates_batch_without_mutating_domain_events():
    cursor, connection = _mock_database([])
    with patch("psycopg.connect", return_value=nullcontext(connection)):
        anchor.mark_confirmed(uuid4(), 1234)

    sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
    assert "UPDATE anchor_batches" in sql
    assert "UPDATE domain_events" not in sql


def test_failure_updates_batch_without_mutating_domain_events():
    cursor, connection = _mock_database([])
    with patch("psycopg.connect", return_value=nullcontext(connection)):
        anchor.mark_failed(uuid4(), "provider failed")

    sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
    assert "UPDATE anchor_batches" in sql
    assert "UPDATE domain_events" not in sql
