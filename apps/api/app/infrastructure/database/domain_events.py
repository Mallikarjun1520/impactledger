"""Persistence for the immutable domain-event log (migration 016, ADR-006).

The caller supplies a ``DomainEventInput``. This module reserves the next
per-org sequence + prev_hash via ``domain_events_next_seq``, builds the
canonical JSON with that seq/prev_hash, hashes it, INSERTs the row, and
closes the chain with ``domain_events_record_hash`` — all inside one
transaction.

Callers are expected to run their own operational INSERT (contribution,
allocation, ...) in the SAME transaction; the helper here exposes a
``record_within`` variant that accepts an open connection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import settings
from app.domain.events import DomainEventInput
from app.domain.hashing import hash_payload


def _record_in_txn(
    connection: psycopg.Connection,
    event: DomainEventInput,
    occurred_at: datetime | None = None,
) -> tuple[UUID, str, int]:
    """Insert ``event`` inside an already-open ``connection`` (autocommit off).
    Returns ``(event_id, hash_hex, seq)``."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT seq, prev_hash FROM domain_events_next_seq(%s)",
            (event.organization_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Failed to allocate domain_events sequence")
        seq, prev_hash = row

        canonical = event.canonical_payload(seq=seq, prev_hash=prev_hash,
                                            occurred_at=occurred_at)
        hash_hex, canonical_bytes = hash_payload(canonical)

        event_id = uuid4()
        cursor.execute(
            """
            INSERT INTO domain_events (
                id, organization_id, event_type, schema_version,
                canonical_json, hash, prev_hash, seq,
                aggregate_type, aggregate_id, performed_by,
                anchor_status, created_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                'PENDING', NOW()
            )
            """,
            (
                event_id,
                event.organization_id,
                event.event_type.value,
                event.schema_version,
                Jsonb(canonical),
                hash_hex,
                prev_hash,
                seq,
                event.aggregate_type,
                event.aggregate_id,
                event.performed_by,
            ),
        )

        cursor.execute(
            "SELECT domain_events_record_hash(%s, %s)",
            (event.organization_id, hash_hex),
        )

    return event_id, hash_hex, seq


def record_event(event: DomainEventInput, occurred_at: datetime | None = None
                 ) -> tuple[UUID, str, int]:
    """Record a single event in its own transaction (convenience wrapper)."""
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            return _record_in_txn(connection, event, occurred_at)


def record_events_with_provenance(
    events: Iterable[DomainEventInput],
    edges: Iterable[tuple[int, int, str]] = (),
) -> list[tuple[UUID, str, int]]:
    """Record several events atomically and optionally add provenance edges.

    ``edges`` items are ``(from_index, to_index, relation)``, referring to the
    ``events`` list positions. All must belong to the same organization.
    """
    events_list = list(events)
    if not events_list:
        return []
    org = events_list[0].organization_id
    if any(e.organization_id != org for e in events_list):
        raise ValueError("record_events_with_provenance requires one organization")

    now = datetime.now(timezone.utc)
    results: list[tuple[UUID, str, int]] = []
    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            for event in events_list:
                results.append(_record_in_txn(connection, event, occurred_at=now))
            with connection.cursor() as cursor:
                for from_i, to_i, relation in edges:
                    cursor.execute(
                        """
                        INSERT INTO provenance_edges (
                            organization_id, from_event_id, to_event_id, relation
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (org, results[from_i][0], results[to_i][0], relation),
                    )
    return results


__all__ = [
    "_record_in_txn",
    "record_event",
    "record_events_with_provenance",
]
