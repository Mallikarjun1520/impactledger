CREATE TABLE distributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    relief_event_id UUID NOT NULL
        REFERENCES relief_events(id)
        ON DELETE RESTRICT,

    resource_batch_id UUID NOT NULL
        REFERENCES resource_batches(id)
        ON DELETE RESTRICT,

    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    quantity NUMERIC(14, 3) NOT NULL
        CHECK (quantity > 0),

    destination TEXT NOT NULL,

    beneficiary_count INTEGER
        CHECK (beneficiary_count IS NULL OR beneficiary_count >= 0),

    notes TEXT,

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);