-- Rulebook §6 (fund pools) + restriction semantics.

CREATE TYPE contribution_restriction_scope AS ENUM (
    'UNRESTRICTED',
    'INITIATIVE',
    'CATEGORY'
);

CREATE TABLE fund_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,

    -- restriction shape of contributions this pool accepts
    restriction_scope contribution_restriction_scope
        NOT NULL DEFAULT 'UNRESTRICTED',
    initiative_id UUID,                 -- required iff scope = INITIATIVE
    category TEXT,                      -- required iff scope = CATEGORY

    currency CHAR(3) NOT NULL DEFAULT 'INR',

    is_closed BOOLEAN NOT NULL DEFAULT FALSE,

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, slug),
    UNIQUE (id, organization_id),

    CONSTRAINT fund_pools_initiative_org_fk
        FOREIGN KEY (initiative_id, organization_id)
        REFERENCES initiatives (id, organization_id)
        ON DELETE RESTRICT,

    CONSTRAINT fund_pools_scope_shape
        CHECK (
            (restriction_scope = 'UNRESTRICTED' AND initiative_id IS NULL AND category IS NULL)
         OR (restriction_scope = 'INITIATIVE'   AND initiative_id IS NOT NULL AND category IS NULL)
         OR (restriction_scope = 'CATEGORY'     AND initiative_id IS NULL AND category IS NOT NULL)
        )
);

CREATE INDEX fund_pools_org_scope_idx
    ON fund_pools (organization_id, restriction_scope);

-- Contributions can now belong to a pool. Legacy contributions with a
-- null fund_pool_id remain unassigned and are eligible for later
-- assignment.
ALTER TABLE contributions
    ADD COLUMN fund_pool_id UUID,
    ADD COLUMN restriction_scope contribution_restriction_scope
        NOT NULL DEFAULT 'UNRESTRICTED',
    ADD COLUMN initiative_id UUID,
    ADD COLUMN category TEXT,
    ADD COLUMN contributor_metadata JSONB
        NOT NULL DEFAULT '{}'::jsonb,           -- PII stays here, RLS locked
    ADD COLUMN external_reference TEXT;          -- payment gateway id, idempotency

ALTER TABLE contributions
    ADD CONSTRAINT contributions_fund_pool_org_fk
    FOREIGN KEY (fund_pool_id, organization_id)
    REFERENCES fund_pools (id, organization_id)
    ON DELETE RESTRICT;

ALTER TABLE contributions
    ADD CONSTRAINT contributions_initiative_org_fk
    FOREIGN KEY (initiative_id, organization_id)
    REFERENCES initiatives (id, organization_id)
    ON DELETE RESTRICT;

ALTER TABLE contributions
    ADD CONSTRAINT contributions_scope_shape
    CHECK (
        (restriction_scope = 'UNRESTRICTED' AND initiative_id IS NULL AND category IS NULL)
     OR (restriction_scope = 'INITIATIVE'   AND initiative_id IS NOT NULL AND category IS NULL)
     OR (restriction_scope = 'CATEGORY'     AND initiative_id IS NULL AND category IS NOT NULL)
    );

CREATE INDEX contributions_pool_status_idx
    ON contributions (fund_pool_id, status);
