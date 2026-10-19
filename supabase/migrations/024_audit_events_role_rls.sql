-- Restrict raw audit-event reads to organization admins and auditors.
-- The service-role write policies from migration 021 remain available to the API.

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

CREATE POLICY audit_logs_service_role ON audit_logs
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS audit_events_select_member ON audit_events;

CREATE POLICY audit_events_select_privileged ON audit_events
    FOR SELECT TO authenticated
    USING (
        organization_id IS NOT NULL
        AND is_org_role(organization_id, ARRAY['ADMIN', 'AUDITOR'])
    );
