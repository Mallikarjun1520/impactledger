CREATE TYPE resource_event_type AS ENUM (
    'RECEIVED',
    'TRANSFER_OUT',
    'TRANSFER_IN',
    'DISTRIBUTED',
    'DAMAGED',
    'ADJUSTED'
);

CREATE TABLE resource_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    resource_batch_id UUID NOT NULL
        REFERENCES resource_batches(id)
        ON DELETE RESTRICT,

    event_type resource_event_type NOT NULL,

    quantity NUMERIC(14, 3) NOT NULL
        CHECK (quantity > 0),

    location TEXT NOT NULL,

    performed_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    reason TEXT,

    transfer_id UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);