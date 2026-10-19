-- Rulebook §17: two-layer authorization. Backend is layer 1; RLS is layer 2.
-- Every tenant-owned table gets:
--   * RLS enabled
--   * A SELECT policy: user must be a member of the row's organization
--   * Restrictive WRITE policies delegated to service_role (backend uses it).
-- The anon key can only read the sanitized public views (migration 021),
-- never the raw tables.
--
-- Helper: is the current auth.uid() a member of the org?

CREATE OR REPLACE FUNCTION is_org_member(org UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
    SELECT EXISTS (
        SELECT 1
          FROM public.organization_members m
         WHERE m.organization_id = org
           AND m.user_id = auth.uid()
    );
$$;

CREATE OR REPLACE FUNCTION is_org_role(org UUID, roles TEXT[])
RETURNS BOOLEAN
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
    SELECT EXISTS (
        SELECT 1
          FROM public.organization_members m
         WHERE m.organization_id = org
           AND m.user_id = auth.uid()
           AND m.role::TEXT = ANY (roles)
    );
$$;

-- Enable RLS on every operational table.
DO $$
DECLARE t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'organizations',
        'organization_members',
        'initiatives',
        'fund_pools',
        'contributions',
        'allocations',
        'vendors',
        'commitments',
        'purchase_orders',
        'payments',
        'resource_types',
        'resource_batches',
        'resource_events',
        'relief_events',
        'distributions',
        'evidence',
        'evidence_links',
        'domain_events',
        'provenance_edges',
        'audit_events',
        'anchor_batches',
        'anchor_batch_items'
    ]) LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', t);
    END LOOP;
END $$;

-- organizations: readable to any member; readable to no one else.
CREATE POLICY organizations_select_member ON organizations
    FOR SELECT USING (is_org_member(id));

-- organization_members: a user always sees their own row; org admins see all.
CREATE POLICY org_members_select_self_or_admin ON organization_members
    FOR SELECT USING (
        user_id = auth.uid()
        OR is_org_role(organization_id, ARRAY['ADMIN'])
    );

-- Generic per-table SELECT policy factory: readable to any member.
DO $$
DECLARE t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'initiatives',
        'fund_pools',
        'contributions',
        'allocations',
        'vendors',
        'commitments',
        'purchase_orders',
        'payments',
        'resource_types',
        'resource_batches',
        'resource_events',
        'relief_events',
        'distributions',
        'evidence',
        'evidence_links',
        'domain_events',
        'provenance_edges',
        'audit_events',
        'anchor_batches',
        'anchor_batch_items'
    ]) LOOP
        EXECUTE format($f$
            CREATE POLICY %I_select_member ON %I
            FOR SELECT USING (is_org_member(organization_id));
        $f$, t, t);
    END LOOP;
END $$;

-- Contributor PII lockdown: contributor_metadata is not returned to
-- non-admin members. We do this via a column-privilege revoke rather
-- than a per-column RLS (Postgres RLS is row-level).
REVOKE SELECT (contributor_metadata) ON contributions FROM authenticated;
GRANT  SELECT (contributor_metadata) ON contributions TO service_role;

-- Writes: only service_role (used by the FastAPI backend) can INSERT /
-- UPDATE / DELETE. The `authenticated` role reaches the DB only through
-- SELECT + the sanitized public views + service-role RPCs.
DO $$
DECLARE t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'organizations',
        'organization_members',
        'initiatives',
        'fund_pools',
        'contributions',
        'allocations',
        'vendors',
        'commitments',
        'purchase_orders',
        'payments',
        'resource_types',
        'resource_batches',
        'resource_events',
        'relief_events',
        'distributions',
        'evidence',
        'evidence_links',
        'domain_events',
        'provenance_edges',
        'audit_events',
        'anchor_batches',
        'anchor_batch_items'
    ]) LOOP
        EXECUTE format($f$
            CREATE POLICY %I_write_service ON %I
            FOR ALL TO service_role USING (true) WITH CHECK (true);
        $f$, t, t);
    END LOOP;
END $$;
