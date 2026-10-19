-- Rulebook §11 evidence model. Bytes in Supabase Storage; metadata + hash here.

CREATE TYPE evidence_kind AS ENUM (
    'INVOICE',
    'RECEIPT',
    'DELIVERY_NOTE',
    'GOODS_RECEIPT',
    'BANK_STATEMENT',
    'PAYMENT_RECEIPT',
    'DONATION_RECEIPT',
    'STOCK_COUNT',
    'DAMAGE_REPORT',
    'DISPOSAL_RECORD',
    'PHOTO',
    'OTHER'
);

CREATE TYPE evidence_status AS ENUM (
    'UPLOADED',
    'PROCESSING',
    'EXTRACTED',
    'VERIFIED',
    'MISMATCH',
    'NEEDS_REVIEW',
    'REJECTED'
);

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    kind evidence_kind NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    content_sha256 CHAR(64) NOT NULL,           -- hex; unique per org
    storage_path TEXT NOT NULL,                 -- e.g. org/{org_id}/evidence/{id}
    status evidence_status NOT NULL DEFAULT 'UPLOADED',

    extracted_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_notes TEXT,

    uploaded_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, content_sha256),
    UNIQUE (id, organization_id)
);

CREATE INDEX evidence_org_status_idx
    ON evidence (organization_id, status);

-- m:n between evidence and domain events (added in 016).
CREATE TABLE evidence_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    evidence_id UUID NOT NULL,
    domain_event_id UUID NOT NULL,        -- FK added after domain_events exists

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (evidence_id, domain_event_id),
    CONSTRAINT evidence_links_evidence_org_fk
        FOREIGN KEY (evidence_id, organization_id)
        REFERENCES evidence (id, organization_id)
        ON DELETE RESTRICT
);
