CREATE TYPE allocation_status AS ENUM (
    'PENDING',
    'APPROVED',
    'CANCELLED'
);

CREATE TABLE allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    contribution_id UUID NOT NULL
        REFERENCES contributions(id)
        ON DELETE RESTRICT,

    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    amount NUMERIC(14, 2) NOT NULL
        CHECK (amount > 0),

    purpose TEXT NOT NULL,

    status allocation_status NOT NULL
        DEFAULT 'PENDING',

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);