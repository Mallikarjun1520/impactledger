-- Rulebook §6 (procurement) + §9 (financial↔physical bridge).

CREATE TABLE vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    name TEXT NOT NULL,
    legal_name TEXT,
    tax_id TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    address JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, name),
    UNIQUE (id, organization_id)
);

-- Extend allocations so they can also draw from a pool (rulebook §6).
ALTER TABLE allocations
    ADD COLUMN fund_pool_id UUID,
    ADD COLUMN initiative_id UUID,
    ADD COLUMN purpose_category TEXT,
    ADD COLUMN currency CHAR(3) NOT NULL DEFAULT 'INR';

ALTER TABLE allocations
    ADD CONSTRAINT allocations_fund_pool_org_fk
    FOREIGN KEY (fund_pool_id, organization_id)
    REFERENCES fund_pools (id, organization_id)
    ON DELETE RESTRICT;

ALTER TABLE allocations
    ADD CONSTRAINT allocations_initiative_org_fk
    FOREIGN KEY (initiative_id, organization_id)
    REFERENCES initiatives (id, organization_id)
    ON DELETE RESTRICT;

ALTER TABLE allocations
    ADD CONSTRAINT allocations_id_organization_unique
    UNIQUE (id, organization_id);

CREATE TYPE commitment_status AS ENUM (
    'ACTIVE',
    'FULFILLED',
    'CANCELLED'
);

CREATE TABLE commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    allocation_id UUID NOT NULL,
    vendor_id UUID,

    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    description TEXT NOT NULL,
    status commitment_status NOT NULL DEFAULT 'ACTIVE',

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (id, organization_id),

    CONSTRAINT commitments_allocation_org_fk
        FOREIGN KEY (allocation_id, organization_id)
        REFERENCES allocations (id, organization_id)
        ON DELETE RESTRICT,

    CONSTRAINT commitments_vendor_org_fk
        FOREIGN KEY (vendor_id, organization_id)
        REFERENCES vendors (id, organization_id)
        ON DELETE RESTRICT
);

CREATE INDEX commitments_alloc_idx
    ON commitments (allocation_id, status);

CREATE TYPE purchase_order_status AS ENUM (
    'DRAFT',
    'AWAITING_APPROVAL',
    'APPROVED',
    'RECEIVED',
    'CLOSED',
    'CANCELLED'
);

CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    commitment_id UUID NOT NULL,
    vendor_id UUID NOT NULL,
    po_number TEXT NOT NULL,
    status purchase_order_status NOT NULL DEFAULT 'DRAFT',

    total_amount NUMERIC(14, 2) NOT NULL CHECK (total_amount > 0),
    tax_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    shipping_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (shipping_amount >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',

    line_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- resource_type_id references remain optional inside the JSON to keep
    -- the row shape simple; the receipt event links to concrete batches.

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,
    approved_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, po_number),
    UNIQUE (id, organization_id),

    CONSTRAINT purchase_orders_commitment_org_fk
        FOREIGN KEY (commitment_id, organization_id)
        REFERENCES commitments (id, organization_id)
        ON DELETE RESTRICT,

    CONSTRAINT purchase_orders_vendor_org_fk
        FOREIGN KEY (vendor_id, organization_id)
        REFERENCES vendors (id, organization_id)
        ON DELETE RESTRICT,

    CONSTRAINT purchase_orders_approval_shape
        CHECK ((approved_by IS NULL) = (approved_at IS NULL))
);

CREATE INDEX purchase_orders_status_idx
    ON purchase_orders (organization_id, status);

CREATE TYPE payment_method AS ENUM (
    'BANK_TRANSFER',
    'UPI',
    'CARD',
    'CASH',
    'CHEQUE',
    'OTHER'
);

CREATE TYPE payment_status AS ENUM (
    'PENDING',
    'COMPLETED',
    'FAILED',
    'REFUNDED'
);

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    purchase_order_id UUID NOT NULL,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    method payment_method NOT NULL,
    status payment_status NOT NULL DEFAULT 'PENDING',

    reference TEXT,                       -- bank reference / gateway id
    paid_at TIMESTAMPTZ,

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (id, organization_id),

    CONSTRAINT payments_po_org_fk
        FOREIGN KEY (purchase_order_id, organization_id)
        REFERENCES purchase_orders (id, organization_id)
        ON DELETE RESTRICT
);

CREATE INDEX payments_po_status_idx
    ON payments (purchase_order_id, status);

-- Link resource batches to their originating PO where applicable.
ALTER TABLE resource_batches
    ADD COLUMN purchase_order_id UUID;

ALTER TABLE resource_batches
    ADD CONSTRAINT resource_batches_po_org_fk
    FOREIGN KEY (purchase_order_id, organization_id)
    REFERENCES purchase_orders (id, organization_id)
    ON DELETE RESTRICT;
