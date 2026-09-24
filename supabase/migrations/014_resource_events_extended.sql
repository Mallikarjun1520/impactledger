-- Rulebook §8 physical lifecycle: existing resource_event_type is
-- RECEIVED/TRANSFER_OUT/TRANSFER_IN/DISTRIBUTED/DAMAGED/ADJUSTED.
-- Extend it to cover DISPATCH / DELIVERY / LOST / DISPOSED so we can
-- represent the full receipt → dispatch → delivery → distribution chain.

ALTER TYPE resource_event_type ADD VALUE IF NOT EXISTS 'DISPATCHED';
ALTER TYPE resource_event_type ADD VALUE IF NOT EXISTS 'DELIVERED';
ALTER TYPE resource_event_type ADD VALUE IF NOT EXISTS 'LOST';
ALTER TYPE resource_event_type ADD VALUE IF NOT EXISTS 'DISPOSED';

-- A resource event may reference an initiative (why the movement happened),
-- a purchase order (which receipt it fulfills), or a distribution destination.
ALTER TABLE resource_events
    ADD COLUMN organization_id UUID,
    ADD COLUMN initiative_id UUID,
    ADD COLUMN purchase_order_id UUID,
    ADD COLUMN destination TEXT;

-- Backfill organization_id from parent batch (safe: batches carry org).
UPDATE resource_events e
   SET organization_id = b.organization_id
  FROM resource_batches b
 WHERE e.resource_batch_id = b.id
   AND e.organization_id IS NULL;

ALTER TABLE resource_events
    ALTER COLUMN organization_id SET NOT NULL;

ALTER TABLE resource_events
    ADD CONSTRAINT resource_events_batch_org_fk
    FOREIGN KEY (resource_batch_id, organization_id)
    REFERENCES resource_batches (id, organization_id)
    ON DELETE RESTRICT;

ALTER TABLE resource_events
    ADD CONSTRAINT resource_events_initiative_org_fk
    FOREIGN KEY (initiative_id, organization_id)
    REFERENCES initiatives (id, organization_id)
    ON DELETE RESTRICT;

ALTER TABLE resource_events
    ADD CONSTRAINT resource_events_po_org_fk
    FOREIGN KEY (purchase_order_id, organization_id)
    REFERENCES purchase_orders (id, organization_id)
    ON DELETE RESTRICT;

CREATE INDEX resource_events_batch_time_idx
    ON resource_events (resource_batch_id, created_at DESC);
