CREATE TABLE resource_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    resource_type_id UUID NOT NULL
        REFERENCES resource_types(id)
        ON DELETE RESTRICT,

    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    batch_code TEXT NOT NULL,

    quantity NUMERIC(14, 3) NOT NULL
        CHECK (quantity > 0),

    source_description TEXT,

    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    location TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, batch_code)
);