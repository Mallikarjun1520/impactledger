-- Day 2 tenant-integrity hardening
--
-- These composite foreign keys ensure that tenant-owned child records
-- cannot reference records belonging to another organization.

ALTER TABLE resource_types
    ADD CONSTRAINT resource_types_id_organization_unique
    UNIQUE (id, organization_id);

ALTER TABLE resource_batches
    ADD CONSTRAINT resource_batches_id_organization_unique
    UNIQUE (id, organization_id);

ALTER TABLE contributions
    ADD CONSTRAINT contributions_id_organization_unique
    UNIQUE (id, organization_id);

ALTER TABLE relief_events
    ADD CONSTRAINT relief_events_id_organization_unique
    UNIQUE (id, organization_id);


ALTER TABLE resource_batches
    ADD CONSTRAINT resource_batches_resource_type_org_fk
    FOREIGN KEY (resource_type_id, organization_id)
    REFERENCES resource_types (id, organization_id)
    ON DELETE RESTRICT;


ALTER TABLE allocations
    ADD CONSTRAINT allocations_contribution_org_fk
    FOREIGN KEY (contribution_id, organization_id)
    REFERENCES contributions (id, organization_id)
    ON DELETE RESTRICT;


ALTER TABLE distributions
    ADD CONSTRAINT distributions_relief_event_org_fk
    FOREIGN KEY (relief_event_id, organization_id)
    REFERENCES relief_events (id, organization_id)
    ON DELETE RESTRICT;


ALTER TABLE distributions
    ADD CONSTRAINT distributions_resource_batch_org_fk
    FOREIGN KEY (resource_batch_id, organization_id)
    REFERENCES resource_batches (id, organization_id)
    ON DELETE RESTRICT;
