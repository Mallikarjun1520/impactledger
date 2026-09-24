-- Demo seed for the canonical scenarios in the rulebook §28.
-- The seed keeps auth.users out of scope; user ids are placeholders that
-- match the ones the local Supabase dev container issues for the
-- test emails admin@demo.local / finance@demo.local / field@demo.local
-- when they sign up. Adjust as needed for your local instance.

-- Idempotency: only insert if the demo org isn't already present.
DO $$
DECLARE
    v_org UUID;
    v_init_relief UUID;
    v_init_medical UUID;
    v_pool_unrestricted UUID;
    v_pool_medical UUID;
BEGIN
    IF EXISTS (SELECT 1 FROM organizations WHERE slug = 'demo-relief') THEN
        RETURN;
    END IF;

    INSERT INTO organizations (name, slug, description, lifecycle, verified_at)
    VALUES ('Demo Relief Foundation', 'demo-relief',
            'Rulebook §28 canonical demo tenant.',
            'ACTIVE', NOW())
    RETURNING id INTO v_org;

    INSERT INTO initiatives (organization_id, name, slug, category, status, starts_at)
    VALUES
      (v_org, 'Flood Relief 2026', 'flood-relief-2026', 'shelter', 'ACTIVE', NOW()),
      (v_org, 'Medical Support Program', 'medical-support', 'medical', 'ACTIVE', NOW())
    RETURNING id INTO v_init_relief;

    SELECT id INTO v_init_medical
      FROM initiatives
     WHERE organization_id = v_org AND slug = 'medical-support';

    INSERT INTO fund_pools (organization_id, name, slug, restriction_scope, currency)
    VALUES (v_org, 'General Emergency Pool', 'general-emergency',
            'UNRESTRICTED', 'INR')
    RETURNING id INTO v_pool_unrestricted;

    INSERT INTO fund_pools (organization_id, name, slug, restriction_scope,
                             initiative_id, currency)
    VALUES (v_org, 'Medical-Restricted Pool', 'medical-restricted',
            'INITIATIVE', v_init_medical, 'INR')
    RETURNING id INTO v_pool_medical;

    -- Scenario 1: aggregated micro-donations
    INSERT INTO contributions (organization_id, fund_pool_id, restriction_scope,
                               amount, currency, visibility, status, received_at)
    SELECT v_org, v_pool_unrestricted, 'UNRESTRICTED',
           amt, 'INR', 'ANONYMOUS', 'CONFIRMED', NOW()
      FROM (VALUES (40::NUMERIC), (50), (100), (500), (1000),
                   (40), (50), (100), (500), (1000)) AS t(amt);

    -- Scenario 2: restricted donations
    INSERT INTO contributions (organization_id, fund_pool_id, restriction_scope,
                               initiative_id, amount, currency, visibility,
                               status, received_at)
    VALUES
      (v_org, v_pool_medical, 'INITIATIVE', v_init_medical,
       25000, 'INR', 'PUBLIC', 'CONFIRMED', NOW()),
      (v_org, v_pool_medical, 'INITIATIVE', v_init_medical,
       10000, 'INR', 'PRIVATE', 'CONFIRMED', NOW());

    -- Vendors + a demo commitment/PO/payment chain (scenario 3)
    INSERT INTO vendors (organization_id, name, legal_name, contact_email)
    VALUES (v_org, 'Blankets India Pvt. Ltd.', 'Blankets India Pvt. Ltd.',
            'sales@blanketsindia.example');

    INSERT INTO resource_types (organization_id, name, unit)
    VALUES (v_org, 'Blankets', 'unit'),
           (v_org, 'Food Kits', 'unit'),
           (v_org, 'Medicine Kits', 'unit');
END $$;
