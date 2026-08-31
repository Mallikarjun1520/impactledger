CREATE TYPE contribution_visibility AS ENUM (
    'PUBLIC',
    'PRIVATE',
    'ANONYMOUS'
);

CREATE TYPE contribution_status AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED'
);

CREATE TABLE contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    contributor_user_id UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    amount NUMERIC(14, 2) NOT NULL
        CHECK (amount > 0),

    currency CHAR(3) NOT NULL DEFAULT 'INR',

    visibility contribution_visibility NOT NULL
        DEFAULT 'PRIVATE',

    status contribution_status NOT NULL
        DEFAULT 'PENDING',

    received_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);