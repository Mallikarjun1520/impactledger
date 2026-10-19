-- ADR-006 belt-and-suspenders: enforce immutability at the DB layer.
-- Committed rows in these tables cannot be UPDATEd or DELETEd.

CREATE OR REPLACE FUNCTION forbid_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Row in % is immutable and cannot be % (id=%); record a new event instead.',
        TG_TABLE_NAME, TG_OP, COALESCE(OLD.id::text, NEW.id::text)
        USING ERRCODE = 'restrict_violation';
END;
$$;

-- domain_events is strictly append-only.
CREATE TRIGGER domain_events_forbid_mutation
BEFORE UPDATE OR DELETE ON domain_events
FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- provenance_edges is strictly append-only.
CREATE TRIGGER provenance_edges_forbid_mutation
BEFORE UPDATE OR DELETE ON provenance_edges
FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- anchor_batch_items is append-only. The parent anchor_batches row is
-- allowed to update status/tx_hash/block_number after submission, so it
-- is NOT locked.
CREATE TRIGGER anchor_batch_items_forbid_mutation
BEFORE UPDATE OR DELETE ON anchor_batch_items
FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- audit_events is append-only.
CREATE TRIGGER audit_events_forbid_mutation
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
