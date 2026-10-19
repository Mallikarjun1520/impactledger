-- Demo seed: a complete, repeatable Flood Relief 2026 funding -> procurement
-- -> receipt -> distribution lifecycle for LOCAL development only.
--
-- Prerequisites (already provided by supabase/seed.sql):
--   * organization slug 'demo-relief'
--   * initiative  slug 'flood-relief-2026'
--
-- This script is idempotent: every entity is resolved by a natural key and
-- inserted only when missing, so it may be run repeatedly. It intentionally
-- does NOT create auth.users, organization_members, domain_events or
-- anchor_batches:
--   * auth users must be real local users (run the canonical seed + sign-up
--     flow first); the actor for approved_by/created_by is resolved below.
--   * domain_events must be produced by the application's canonical hashing
--     (app/domain/hashing.py); the SQL seed must not fabricate them.
--   * anchor_batches require a real on-chain submission and are out of scope.
--
-- Usage (local Supabase Postgres on loopback 54322):
--   psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" \
--        -f supabase/seed.sql -f supabase/demo_flood_relief.sql
--
-- Override the actor explicitly if the local demo user's email differs:
--   psql "$DATABASE_URL" -c "SET impactledger.demo_actor = '<uuid>';" \
--        -f supabase/demo_flood_relief.sql
-- (SET and -f cannot share a session from the shell; either set it inside a
-- single psql session or rely on admin@demo.local / an existing ADMIN member.)

DO $$
DECLARE
    v_org          UUID;
    v_initiative   UUID;
    v_actor        UUID;
    v_vendor       UUID;
    v_resource_type UUID;
    v_contribution UUID;
    v_allocation   UUID;
    v_commitment   UUID;
    v_po           UUID;
    v_payment      UUID;
    v_batch        UUID;
    v_relief_event UUID;
    v_distribution UUID;
BEGIN
    -- ------------------------------------------------------------------
    -- 1. Resolve the demo tenant and initiative (created by seed.sql).
    -- ------------------------------------------------------------------
    SELECT id INTO v_org
      FROM organizations
     WHERE slug = 'demo-relief';

    IF v_org IS NULL THEN
        RAISE EXCEPTION
            'demo-relief organization not found; run supabase/seed.sql first';
    END IF;

    SELECT id INTO v_initiative
      FROM initiatives
     WHERE organization_id = v_org
       AND slug = 'flood-relief-2026';

    IF v_initiative IS NULL THEN
        RAISE EXCEPTION
            'flood-relief-2026 initiative not found; run supabase/seed.sql first';
    END IF;

    -- Make the tenant/initiative publicly visible only if they are still in a
    -- pre-public (draft) state. No-op under the canonical seed, which already
    -- sets both to ACTIVE.
    UPDATE organizations
       SET lifecycle = 'ACTIVE'
     WHERE id = v_org
       AND lifecycle NOT IN ('VERIFIED', 'ACTIVE', 'SUSPENDED', 'CLOSED');

    UPDATE initiatives
       SET status = 'ACTIVE'
     WHERE id = v_initiative
       AND status NOT IN ('ACTIVE', 'CLOSING', 'CLOSED');

    -- ------------------------------------------------------------------
    -- 2. Resolve the actor for approved_by / created_by.
    --    purchase_orders.approved_by is a hard FK to auth.users, so a real
    --    local user is required. Never fabricate one.
    -- ------------------------------------------------------------------
    v_actor := NULLIF(current_setting('impactledger.demo_actor', true), '')::uuid;

    IF v_actor IS NULL THEN
        SELECT id INTO v_actor
          FROM auth.users
         WHERE email = 'admin@demo.local'
         LIMIT 1;
    END IF;

    IF v_actor IS NULL THEN
        SELECT user_id INTO v_actor
          FROM organization_members
         WHERE organization_id = v_org
           AND role = 'ADMIN'
         ORDER BY created_at
         LIMIT 1;
    END IF;

    IF v_actor IS NULL THEN
        SELECT user_id INTO v_actor
          FROM organization_members
         WHERE organization_id = v_org
         ORDER BY created_at
         LIMIT 1;
    END IF;

    IF v_actor IS NULL THEN
        RAISE EXCEPTION
            'No local demo user found for organization demo-relief. Create an '
            'auth user (e.g. admin@demo.local) and an organization_members row, '
            'or SET impactledger.demo_actor = ''<uuid>'' before running.';
    END IF;

    -- ------------------------------------------------------------------
    -- 3. Vendor + resource type (reuse the canonical seed's rows if present).
    -- ------------------------------------------------------------------
    SELECT id INTO v_vendor
      FROM vendors
     WHERE organization_id = v_org
       AND name = 'Blankets India Pvt. Ltd.';

    IF v_vendor IS NULL THEN
        INSERT INTO vendors (organization_id, name, legal_name, contact_email)
        VALUES (v_org, 'Blankets India Pvt. Ltd.', 'Blankets India Pvt. Ltd.',
                'sales@blanketsindia.example')
        RETURNING id INTO v_vendor;
    END IF;

    SELECT id INTO v_resource_type
      FROM resource_types
     WHERE organization_id = v_org
       AND name = 'Blankets';

    IF v_resource_type IS NULL THEN
        INSERT INTO resource_types (organization_id, name, unit)
        VALUES (v_org, 'Blankets', 'unit')
        RETURNING id INTO v_resource_type;
    END IF;

    -- ------------------------------------------------------------------
    -- 4. Confirmed contribution explicitly restricted to flood-relief-2026.
    --    Amount: INR 50,000.
    -- ------------------------------------------------------------------
    SELECT id INTO v_contribution
      FROM contributions
     WHERE organization_id = v_org
       AND external_reference = 'demo-flood-relief-2026-contribution-50000';

    IF v_contribution IS NULL THEN
        INSERT INTO contributions (
            organization_id, restriction_scope, initiative_id, amount, currency,
            visibility, status, received_at, external_reference
        )
        VALUES (
            v_org, 'INITIATIVE', v_initiative, 50000, 'INR',
            'PUBLIC', 'CONFIRMED', NOW(),
            'demo-flood-relief-2026-contribution-50000'
        )
        RETURNING id INTO v_contribution;
    END IF;

    -- ------------------------------------------------------------------
    -- 5. Approved allocation from that contribution. Amount: INR 30,000.
    -- ------------------------------------------------------------------
    SELECT id INTO v_allocation
      FROM allocations
     WHERE organization_id = v_org
       AND contribution_id = v_contribution
       AND purpose = 'Flood Relief 2026 - emergency shelter procurement';

    IF v_allocation IS NULL THEN
        INSERT INTO allocations (
            contribution_id, organization_id, initiative_id, amount, purpose,
            status, created_by
        )
        VALUES (
            v_contribution, v_org, v_initiative, 30000,
            'Flood Relief 2026 - emergency shelter procurement',
            'APPROVED', v_actor
        )
        RETURNING id INTO v_allocation;
    END IF;

    -- ------------------------------------------------------------------
    -- 6. Commitment to the vendor. Amount: INR 25,000.
    -- ------------------------------------------------------------------
    SELECT id INTO v_commitment
      FROM commitments
     WHERE organization_id = v_org
       AND allocation_id = v_allocation
       AND description = 'Procure 100 emergency blankets for flood relief';

    IF v_commitment IS NULL THEN
        INSERT INTO commitments (
            organization_id, allocation_id, vendor_id, amount, currency,
            description, status, created_by
        )
        VALUES (
            v_org, v_allocation, v_vendor, 25000, 'INR',
            'Procure 100 emergency blankets for flood relief', 'ACTIVE', v_actor
        )
        RETURNING id INTO v_commitment;
    END IF;

    -- ------------------------------------------------------------------
    -- 7. Approved purchase order. Amount: INR 25,000.
    --    approved_by / approved_at must be both set (schema CHECK).
    -- ------------------------------------------------------------------
    SELECT id INTO v_po
      FROM purchase_orders
     WHERE organization_id = v_org
       AND po_number = 'DEMO-FR2026-PO-001';

    IF v_po IS NULL THEN
        INSERT INTO purchase_orders (
            organization_id, commitment_id, vendor_id, po_number, status,
            total_amount, currency, line_items, created_by, approved_by,
            approved_at
        )
        VALUES (
            v_org, v_commitment, v_vendor, 'DEMO-FR2026-PO-001', 'APPROVED',
            25000, 'INR',
            jsonb_build_array(jsonb_build_object(
                'resource_type', 'Blankets',
                'quantity', 100,
                'unit', 'unit',
                'unit_price', 250
            )),
            v_actor, v_actor, NOW()
        )
        RETURNING id INTO v_po;
    END IF;

    -- ------------------------------------------------------------------
    -- 8. Completed payment against the PO. Amount: INR 25,000.
    -- ------------------------------------------------------------------
    SELECT id INTO v_payment
      FROM payments
     WHERE organization_id = v_org
       AND reference = 'DEMO-FR2026-PAY-001';

    IF v_payment IS NULL THEN
        INSERT INTO payments (
            organization_id, purchase_order_id, amount, currency, method,
            status, reference, paid_at, created_by
        )
        VALUES (
            v_org, v_po, 25000, 'INR', 'BANK_TRANSFER', 'COMPLETED',
            'DEMO-FR2026-PAY-001', NOW(), v_actor
        )
        RETURNING id INTO v_payment;
    END IF;

    -- ------------------------------------------------------------------
    -- 9. Resource batch: 100 blankets received against the PO.
    -- ------------------------------------------------------------------
    SELECT id INTO v_batch
      FROM resource_batches
     WHERE organization_id = v_org
       AND batch_code = 'DEMO-FR2026-BLANKETS-001';

    IF v_batch IS NULL THEN
        INSERT INTO resource_batches (
            resource_type_id, organization_id, purchase_order_id, batch_code,
            quantity, source_description, location
        )
        VALUES (
            v_resource_type, v_org, v_po, 'DEMO-FR2026-BLANKETS-001', 100,
            'Demo: received against DEMO-FR2026-PO-001', 'Kochi, Kerala'
        )
        RETURNING id INTO v_batch;
    END IF;

    -- RECEIVED event, explicitly attributed to the initiative and the PO so
    -- the public transparency views can surface it.
    IF NOT EXISTS (
        SELECT 1 FROM resource_events
         WHERE resource_batch_id = v_batch
           AND event_type = 'RECEIVED'
           AND reason = 'Demo: initial blanket batch receipt'
    ) THEN
        INSERT INTO resource_events (
            organization_id, initiative_id, purchase_order_id, resource_batch_id,
            event_type, quantity, location, performed_by, reason
        )
        VALUES (
            v_org, v_initiative, v_po, v_batch,
            'RECEIVED', 100, 'Kochi, Kerala', v_actor,
            'Demo: initial blanket batch receipt'
        );
    END IF;

    -- ------------------------------------------------------------------
    -- 10. Relief event + distribution of 60 blankets to a named destination.
    -- ------------------------------------------------------------------
    SELECT id INTO v_relief_event
      FROM relief_events
     WHERE organization_id = v_org
       AND name = 'Flood Relief 2026 - Blanket Distribution';

    IF v_relief_event IS NULL THEN
        INSERT INTO relief_events (
            organization_id, name, description, location, status, started_at,
            created_by
        )
        VALUES (
            v_org, 'Flood Relief 2026 - Blanket Distribution',
            'Demo distribution of emergency blankets to flood-affected households.',
            'Kochi, Kerala', 'COMPLETED', NOW(), v_actor
        )
        RETURNING id INTO v_relief_event;
    END IF;

    SELECT id INTO v_distribution
      FROM distributions
     WHERE organization_id = v_org
       AND relief_event_id = v_relief_event
       AND resource_batch_id = v_batch;

    IF v_distribution IS NULL THEN
        INSERT INTO distributions (
            relief_event_id, resource_batch_id, organization_id, quantity,
            destination, beneficiary_count, notes, created_by
        )
        VALUES (
            v_relief_event, v_batch, v_org, 60,
            'Government Relief Camp, Kochi', 120,
            'Demo: 60 blankets to 120 households.', v_actor
        )
        RETURNING id INTO v_distribution;
    END IF;

    -- DISTRIBUTED event, attributed to the initiative + PO + destination.
    IF NOT EXISTS (
        SELECT 1 FROM resource_events
         WHERE resource_batch_id = v_batch
           AND event_type = 'DISTRIBUTED'
           AND reason = 'Distribution ' || v_distribution::text
    ) THEN
        INSERT INTO resource_events (
            organization_id, initiative_id, purchase_order_id, resource_batch_id,
            event_type, quantity, location, performed_by, reason, destination
        )
        VALUES (
            v_org, v_initiative, v_po, v_batch,
            'DISTRIBUTED', 60, 'Government Relief Camp, Kochi', v_actor,
            'Distribution ' || v_distribution::text,
            'Government Relief Camp, Kochi'
        );
    END IF;

    -- ------------------------------------------------------------------
    -- 11. Audit trail for the demo distribution (audit_events, not
    --     domain_events).
    -- ------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM audit_events
         WHERE organization_id = v_org
           AND event_type = 'ADMIN_ACTION'
           AND details->>'entity_id' = v_distribution::text
    ) THEN
        INSERT INTO audit_events (organization_id, event_type, user_id, details)
        VALUES (
            v_org, 'ADMIN_ACTION', v_actor,
            jsonb_build_object(
                'action', 'RESOURCE_DISTRIBUTED',
                'entity_type', 'distribution',
                'entity_id', v_distribution::text,
                'seed', 'demo_flood_relief'
            )
        );
    END IF;

    RAISE NOTICE
        'demo_flood_relief seeded: org=%, initiative=%, allocation=%, po=%, '
        'batch=%, distribution=%',
        v_org, v_initiative, v_allocation, v_po, v_batch, v_distribution;
END $$;
