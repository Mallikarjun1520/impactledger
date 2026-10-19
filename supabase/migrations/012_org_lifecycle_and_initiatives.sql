-- Rulebook §4 (organization lifecycle) and §5 (initiatives).
-- Additive: existing rows default to ACTIVE so current tests keep passing.

CREATE TYPE organization_lifecycle AS ENUM (
    'DRAFT',
    'PENDING_VERIFICATION',
    'VERIFIED',
    'ACTIVE',
    'SUSPENDED',
    'CLOSED'
);

ALTER TABLE organizations
    ADD COLUMN lifecycle organization_lifecycle NOT NULL DEFAULT 'ACTIVE',
    ADD COLUMN verified_at TIMESTAMPTZ,
    ADD COLUMN suspended_at TIMESTAMPTZ,
    ADD COLUMN closed_at TIMESTAMPTZ;

CREATE TYPE initiative_status AS ENUM (
    'DRAFT',
    'ACTIVE',
    'CLOSING',
    'CLOSED'
);

CREATE TABLE initiatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,
    category TEXT,                             -- e.g. 'medical', 'shelter', 'food'
    status initiative_status NOT NULL DEFAULT 'DRAFT',

    starts_at TIMESTAMPTZ,
    closes_at TIMESTAMPTZ,

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, slug),
    UNIQUE (id, organization_id),
    CHECK (closes_at IS NULL OR starts_at IS NULL OR closes_at >= starts_at)
);

CREATE INDEX initiatives_org_status_idx
    ON initiatives (organization_id, status);
