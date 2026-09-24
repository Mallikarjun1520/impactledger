"""Persistence for anchor batches (migration 017)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

import psycopg

from app.core.config import settings


@dataclass(frozen=True)
class PendingEvent:
    id: UUID
    hash: str
    seq: int


@dataclass(frozen=True)
class AnchorBatchRow:
    id: UUID
    organization_id: UUID
    merkle_root: str
    event_count: int
    chain_id: int
    contract_address: str | None
    tx_hash: str | None
    block_number: int | None
    status: str
    submitted_at: datetime | None
    confirmed_at: datetime | None
    failure_reason: str | None
    created_at: datetime


def fetch_pending_events(organization_id: UUID, max_events: int) -> list[PendingEvent]:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, hash, seq
                  FROM domain_events
                 WHERE organization_id = %s
                   AND anchor_status = 'PENDING'
                 ORDER BY seq ASC
                 LIMIT %s
                """,
                (organization_id, max_events),
            )
            rows = cursor.fetchall()
    return [PendingEvent(id=r[0], hash=r[1], seq=r[2]) for r in rows]


def create_batch(
    organization_id: UUID,
    events: list[PendingEvent],
    merkle_root_hex: str,
    chain_id: int,
    contract_address: str | None,
) -> AnchorBatchRow:
    """Atomically create the batch row, insert item links, and flip member
    events to BATCHED."""
    batch_id = uuid4()
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO anchor_batches (
                        id, organization_id, merkle_root, event_count,
                        chain_id, contract_address, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'PENDING')
                    RETURNING id, organization_id, merkle_root, event_count,
                              chain_id, contract_address, tx_hash, block_number,
                              status, submitted_at, confirmed_at, failure_reason,
                              created_at
                    """,
                    (
                        batch_id,
                        organization_id,
                        merkle_root_hex,
                        len(events),
                        chain_id,
                        contract_address,
                    ),
                )
                row = cursor.fetchone()

                for idx, ev in enumerate(events):
                    cursor.execute(
                        """
                        INSERT INTO anchor_batch_items (
                            organization_id, anchor_batch_id, domain_event_id,
                            leaf_index, leaf_hash
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (organization_id, batch_id, ev.id, idx, ev.hash),
                    )
                    cursor.execute(
                        """
                        UPDATE domain_events
                           SET anchor_status = 'BATCHED',
                               anchor_batch_id = %s
                         WHERE id = %s AND organization_id = %s
                        """,
                        (batch_id, ev.id, organization_id),
                    )
    return AnchorBatchRow(*row)


def record_submission(
    batch_id: UUID,
    tx_hash: str,
    block_number: int | None,
    contract_address: str,
) -> None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE anchor_batches
                       SET tx_hash = %s,
                           block_number = %s,
                           contract_address = COALESCE(contract_address, %s),
                           status = 'SUBMITTED',
                           submitted_at = NOW()
                     WHERE id = %s
                    """,
                    (tx_hash, block_number, contract_address, batch_id),
                )


def mark_confirmed(batch_id: UUID, block_number: int) -> None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE anchor_batches
                       SET status = 'CONFIRMED',
                           block_number = %s,
                           confirmed_at = NOW()
                     WHERE id = %s
                    """,
                    (block_number, batch_id),
                )
                cursor.execute(
                    """
                    UPDATE domain_events
                       SET anchor_status = 'ANCHORED'
                     WHERE anchor_batch_id = %s
                    """,
                    (batch_id,),
                )


def mark_failed(batch_id: UUID, reason: str) -> None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE anchor_batches
                       SET status = 'FAILED',
                           failure_reason = %s
                     WHERE id = %s
                    """,
                    (reason, batch_id),
                )
                cursor.execute(
                    """
                    UPDATE domain_events
                       SET anchor_status = 'PENDING',
                           anchor_batch_id = NULL
                     WHERE anchor_batch_id = %s
                    """,
                    (batch_id,),
                )


def get_batch(batch_id: UUID) -> AnchorBatchRow | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, organization_id, merkle_root, event_count,
                       chain_id, contract_address, tx_hash, block_number,
                       status, submitted_at, confirmed_at, failure_reason,
                       created_at
                  FROM anchor_batches
                 WHERE id = %s
                """,
                (batch_id,),
            )
            row = cursor.fetchone()
    return AnchorBatchRow(*row) if row else None


def get_batch_leaves(batch_id: UUID) -> list[str]:
    """Return leaf hashes in tree order for proof reconstruction."""
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT leaf_hash
                  FROM anchor_batch_items
                 WHERE anchor_batch_id = %s
                 ORDER BY leaf_index ASC
                """,
                (batch_id,),
            )
            rows = cursor.fetchall()
    return [r[0] for r in rows]


def get_leaf_index(batch_id: UUID, event_id: UUID) -> int | None:
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT leaf_index
                  FROM anchor_batch_items
                 WHERE anchor_batch_id = %s AND domain_event_id = %s
                """,
                (batch_id, event_id),
            )
            row = cursor.fetchone()
    return int(row[0]) if row else None
