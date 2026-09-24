-- Rulebook §22 + ADR-011.
-- Anchor batches collect PENDING domain_events, compute a Merkle root,
-- and record the on-chain transaction result.

CREATE TYPE anchor_batch_status AS ENUM (
    'PENDING',      -- created, root computed, not yet submitted
    'SUBMITTED',    -- tx sent, awaiting inclusion
    'CONFIRMED',    -- inclusion + confirmations reached
    'FAILED'
);

CREATE TABLE anchor_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE RESTRICT,

    merkle_root CHAR(64) NOT NULL,          -- hex; 32-byte root
    event_count INTEGER NOT NULL CHECK (event_count > 0),

    chain_id BIGINT NOT NULL,               -- 84532 for Base Sepolia
    contract_address TEXT,                  -- deployed anchor contract
    tx_hash TEXT,
    block_number BIGINT,
    submitted_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,

    status anchor_batch_status NOT NULL DEFAULT 'PENDING',
    failure_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (id, organization_id)
);

CREATE INDEX anchor_batches_status_idx
    ON anchor_batches (organization_id, status);

-- Junction: which events belong to which batch, and the leaf index the
-- verifier needs to reconstruct the Merkle proof.
CREATE TABLE anchor_batch_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE RESTRICT,

    anchor_batch_id UUID NOT NULL,
    domain_event_id UUID NOT NULL,
    leaf_index INTEGER NOT NULL CHECK (leaf_index >= 0),
    leaf_hash CHAR(64) NOT NULL,            -- redundant with event.hash but denormalized

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (anchor_batch_id, leaf_index),
    UNIQUE (anchor_batch_id, domain_event_id),

    CONSTRAINT anchor_items_batch_org_fk
        FOREIGN KEY (anchor_batch_id, organization_id)
        REFERENCES anchor_batches (id, organization_id)
        ON DELETE RESTRICT,
    CONSTRAINT anchor_items_event_org_fk
        FOREIGN KEY (domain_event_id, organization_id)
        REFERENCES domain_events (id, organization_id)
        ON DELETE RESTRICT
);

CREATE INDEX anchor_batch_items_batch_idx
    ON anchor_batch_items (anchor_batch_id, leaf_index);

-- Now that anchor_batches exists, tie domain_events.anchor_batch_id back.
ALTER TABLE domain_events
    ADD CONSTRAINT domain_events_anchor_batch_org_fk
    FOREIGN KEY (anchor_batch_id, organization_id)
    REFERENCES anchor_batches (id, organization_id)
    ON DELETE RESTRICT;
