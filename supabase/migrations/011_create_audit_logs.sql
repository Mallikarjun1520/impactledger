-- Migration: 011_create_audit_logs.sql
-- Adds organization-scoped audit log table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES auth.users(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB
);

-- Index for performant queries by organization and time
CREATE INDEX idx_audit_logs_org_ts ON audit_logs (organization_id, timestamp DESC);
