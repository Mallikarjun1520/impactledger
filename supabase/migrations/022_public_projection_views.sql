-- Rulebook §19 + ADR-015. The public/anon key sees only these views;
-- never the raw tables. Discrepancies remain visible (Rule 08).

-- Per-initiative aggregates the public may see.
CREATE OR REPLACE VIEW public_initiative_summary AS
WITH contribs AS (
    SELECT
        i.id AS initiative_id,
        i.organization_id,
        COUNT(c.id) FILTER (WHERE c.status = 'CONFIRMED')          AS contribution_count,
        COALESCE(SUM(c.amount) FILTER (WHERE c.status = 'CONFIRMED'), 0) AS contribution_total
      FROM initiatives i
      LEFT JOIN contributions c
        ON c.initiative_id = i.id
       AND c.organization_id = i.organization_id
     GROUP BY i.id, i.organization_id
),
allocs AS (
    SELECT
        i.id AS initiative_id,
        i.organization_id,
        COALESCE(SUM(a.amount) FILTER (WHERE a.status = 'APPROVED'), 0) AS allocated_total
      FROM initiatives i
      LEFT JOIN allocations a
        ON a.initiative_id = i.id
       AND a.organization_id = i.organization_id
     GROUP BY i.id, i.organization_id
),
payments_agg AS (
    SELECT
        i.id AS initiative_id,
        i.organization_id,
        COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'COMPLETED'), 0) AS paid_total
      FROM initiatives i
      LEFT JOIN allocations   a ON a.initiative_id = i.id AND a.organization_id = i.organization_id
      LEFT JOIN commitments   cm ON cm.allocation_id = a.id AND cm.organization_id = a.organization_id
      LEFT JOIN purchase_orders po ON po.commitment_id = cm.id AND po.organization_id = cm.organization_id
      LEFT JOIN payments      p ON p.purchase_order_id = po.id AND p.organization_id = po.organization_id
     GROUP BY i.id, i.organization_id
)
SELECT
    i.id            AS initiative_id,
    o.slug          AS org_slug,
    o.name          AS org_name,
    i.slug          AS initiative_slug,
    i.name          AS initiative_name,
    i.description,
    i.category,
    i.status,
    i.starts_at,
    i.closes_at,
    c.contribution_count,
    c.contribution_total,
    a.allocated_total,
    p.paid_total,
    (c.contribution_total - a.allocated_total) AS unallocated_total,
    CASE
        WHEN c.contribution_total = 0 THEN 0
        ELSE ROUND((a.allocated_total * 100.0 / c.contribution_total), 2)
    END AS allocation_pct
  FROM initiatives i
  JOIN organizations o ON o.id = i.organization_id
  LEFT JOIN contribs c ON c.initiative_id = i.id
  LEFT JOIN allocs a ON a.initiative_id = i.id
  LEFT JOIN payments_agg p ON p.initiative_id = i.id
 WHERE o.lifecycle IN ('VERIFIED', 'ACTIVE', 'SUSPENDED', 'CLOSED')
   AND i.status IN ('ACTIVE', 'CLOSING', 'CLOSED');

-- Aggregate physical view: how many units of each resource type moved
-- through an initiative.
CREATE OR REPLACE VIEW public_initiative_resources AS
SELECT
    i.id AS initiative_id,
    rt.name AS resource_name,
    rt.unit,
    COALESCE(SUM(CASE WHEN e.event_type = 'RECEIVED' THEN e.quantity END), 0)      AS received,
    COALESCE(SUM(CASE WHEN e.event_type = 'DISTRIBUTED' THEN e.quantity END), 0)   AS distributed,
    COALESCE(SUM(CASE WHEN e.event_type = 'DAMAGED' THEN e.quantity END), 0)       AS damaged,
    COALESCE(SUM(CASE WHEN e.event_type = 'LOST' THEN e.quantity END), 0)          AS lost,
    COALESCE(SUM(CASE WHEN e.event_type = 'DISPOSED' THEN e.quantity END), 0)      AS disposed
  FROM initiatives i
  JOIN resource_events e
    ON e.initiative_id = i.id
   AND e.organization_id = i.organization_id
  JOIN resource_batches b
    ON b.id = e.resource_batch_id
   AND b.organization_id = e.organization_id
  JOIN resource_types rt
    ON rt.id = b.resource_type_id
   AND rt.organization_id = b.organization_id
 GROUP BY i.id, rt.name, rt.unit;

-- Discrepancies (Rule 08): variance between expected and received quantity
-- as recorded on the resource_events feed. Any receipt event whose
-- companion PO expected a different quantity surfaces here.
CREATE OR REPLACE VIEW public_reconciliation_flags AS
SELECT
    e.organization_id,
    e.initiative_id,
    e.resource_batch_id,
    e.id AS event_id,
    e.event_type,
    e.quantity,
    e.reason,
    e.created_at
  FROM resource_events e
 WHERE e.event_type IN ('DAMAGED', 'LOST', 'ADJUSTED')
    OR (e.reason IS NOT NULL AND e.reason ILIKE '%variance%');

-- Anchor batches visible publicly (root + tx hash only).
CREATE OR REPLACE VIEW public_anchor_batches AS
SELECT
    ab.id,
    ab.organization_id,
    ab.merkle_root,
    ab.event_count,
    ab.chain_id,
    ab.contract_address,
    ab.tx_hash,
    ab.block_number,
    ab.status,
    ab.submitted_at,
    ab.confirmed_at
  FROM anchor_batches ab
 WHERE ab.status IN ('SUBMITTED', 'CONFIRMED');

-- Grants: anon reads views, not tables.
GRANT SELECT ON public_initiative_summary   TO anon, authenticated;
GRANT SELECT ON public_initiative_resources TO anon, authenticated;
GRANT SELECT ON public_reconciliation_flags TO anon, authenticated;
GRANT SELECT ON public_anchor_batches       TO anon, authenticated;
