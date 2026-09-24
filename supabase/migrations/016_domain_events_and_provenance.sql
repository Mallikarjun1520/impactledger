-- Rulebook §10 (provenance) + Rule 01 (immutability) + ADR-006.
-- domain_events is append-only. A per-org hash chain lets any auditor
-- verify local integrity independent of the on-chain anchor.

CREATE TYPE domain_event_type AS ENUM (
    'CONTRIBUTION_RECORDED',
    'CONTRIBUTION_CANCELLED',
    'FUND_POOL_CREATED',
    'ALLOCATION_RECORDED',
    'ALLOCATION_CANCELLED',
    'COMMITMENT_CREATED',
    'COMMITMENT_CANCELLED',
    'PURCHASE_ORDER_CREATED',
    'PURCHASE_ORDER_APPROVED',
    'PURCHASE_ORDER_CANCELLED',
    'PAYMENT_RECORDED',
    'PAYMENT_REFUNDED',
    'RESOURCE_RECEIVED',
    'RESOURCE_TRANSFERRED',
    'RESOURCE_DISPATCHED',
    'RESOURCE_DELIVERED',
    'RESOURCE_DISTRIBUTED',
    'RESOURCE_LOST',
    'RESOURCE_DAMAGED',
    'RESOURCE_DISPOSED',
    'RESOURCE_ADJUSTED',
    'EVIDENCE_UPLOADED',
    'EVIDENCE_LINKED',
    'EVIDENCE_VERIFIED',
    'CORRECTION_RECORDED',
    'REVERSAL_RECORDED'
);

CREATE TYPE anchor_status AS ENUM (
    'PENDING',
    'BATCHED',
    'ANCHORED',
    'FAILED'
);

CREATE TABLE domain_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE RESTRICT,             -- never CASCADE — history stays

    event_type domain_event_type NOT NULL,
    schema_version SMALLINT NOT NULL DEFAULT 1,

    -- Canonical JSON: RFC 8785-inspired sorted-keys UTF-8 serialization,
    -- produced by apps/api/app/domain/hashing.py. Stored verbatim.
    canonical_json JSONB NOT NULL,
    hash CHAR(64) NOT NULL,             -- hex SHA-256(canonical_json bytes)
    prev_hash CHAR(64),                 -- previous event hash for this org

    seq BIGINT NOT NULL,                -- monotonic per-org sequence

    aggregate_type TEXT NOT NULL,       -- 'contribution', 'allocation', ...
    aggregate_id UUID,                  -- id of the operational row (if any)

    performed_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    anchor_status anchor_status NOT NULL DEFAULT 'PENDING',
    anchor_batch_id UUID,               -- FK added in 017

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, seq),
    UNIQUE (organization_id, hash),
    UNIQUE (id, organization_id)
);

CREATE INDEX domain_events_org_time_idx
    ON domain_events (organization_id, created_at DESC);
CREATE INDEX domain_events_anchor_status_idx
    ON domain_events (organization_id, anchor_status)
    WHERE anchor_status IN ('PENDING', 'BATCHED');
CREATE INDEX domain_events_aggregate_idx
    ON domain_events (aggregate_type, aggregate_id);

-- Finalize the evidence → domain_events link now that both exist.
ALTER TABLE evidence_links
    ADD CONSTRAINT evidence_links_event_org_fk
    FOREIGN KEY (domain_event_id, organization_id)
    REFERENCES domain_events (id, organization_id)
    ON DELETE RESTRICT;

CREATE TYPE provenance_relation AS ENUM (
    'DERIVED_FROM',
    'REFERENCES',
    'FULFILLS',
    'ALLOCATES_FROM',
    'AFFECTS',
    'CORRECTS',
    'REVERSES'
);

CREATE TABLE provenance_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE RESTRICT,

    from_event_id UUID NOT NULL,
    to_event_id UUID NOT NULL,
    relation provenance_relation NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (from_event_id, to_event_id, relation),

    CONSTRAINT provenance_from_event_org_fk
        FOREIGN KEY (from_event_id, organization_id)
        REFERENCES domain_events (id, organization_id)
        ON DELETE RESTRICT,
    CONSTRAINT provenance_to_event_org_fk
        FOREIGN KEY (to_event_id, organization_id)
        REFERENCES domain_events (id, organization_id)
        ON DELETE RESTRICT,

    CHECK (from_event_id <> to_event_id)
);

CREATE INDEX provenance_from_idx ON provenance_edges (from_event_id, relation);
CREATE INDEX provenance_to_idx   ON provenance_edges (to_event_id, relation);

-- Per-org monotonic sequence generator. Kept in a small helper table to
-- guarantee ordering without a hot single sequence.
CREATE TABLE domain_event_sequences (
    organization_id UUID PRIMARY KEY
        REFERENCES organizations(id) ON DELETE CASCADE,
    last_seq BIGINT NOT NULL DEFAULT 0,
    last_hash CHAR(64)
);

-- Server-side helper: reserve the next (seq, prev_hash) atomically.
-- Callers still compute the canonical_json + hash in app code and INSERT.
CREATE OR REPLACE FUNCTION domain_events_next_seq(p_org UUID)
RETURNS TABLE (seq BIGINT, prev_hash CHAR(64))
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO domain_event_sequences (organization_id, last_seq, last_hash)
    VALUES (p_org, 0, NULL)
    ON CONFLICT (organization_id) DO NOTHING;

    RETURN QUERY
    UPDATE domain_event_sequences
       SET last_seq = last_seq + 1
     WHERE organization_id = p_org
    RETURNING last_seq, last_hash;
END;
$$;

-- Chain-close helper: called immediately after INSERT with the new hash
-- so subsequent reservations see it as prev_hash.
CREATE OR REPLACE FUNCTION domain_events_record_hash(
    p_org UUID,
    p_hash CHAR(64)
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE domain_event_sequences
       SET last_hash = p_hash
     WHERE organization_id = p_org;
END;
$$;
