CREATE TYPE relief_event_status AS ENUM (
    'PLANNED',
    'ACTIVE',
    'COMPLETED',
    'CANCELLED'
);

CREATE TABLE relief_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    name TEXT NOT NULL,

    description TEXT,

    location TEXT NOT NULL,

    status relief_event_status NOT NULL
        DEFAULT 'PLANNED',

    started_at TIMESTAMPTZ,

    ended_at TIMESTAMPTZ,

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        ended_at IS NULL
        OR started_at IS NULL
        OR ended_at >= started_at
    )
);
