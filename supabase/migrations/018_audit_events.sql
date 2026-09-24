-- Rulebook §18. Audit events describe system behavior (login, denial,
-- admin action) and are kept separate from domain_events so a noisy
-- login attempt does not pollute the provenance graph.

CREATE TYPE audit_event_type AS ENUM (
    'LOGIN_SUCCEEDED',
    'LOGIN_FAILED',
    'AUTHORIZATION_DENIED',
    'MEMBER_ADDED',
    'MEMBER_REMOVED',
    'MEMBER_ROLE_CHANGED',
    'PO_APPROVAL_ATTEMPTED',
    'PO_APPROVAL_DENIED_SELF',
    'ADMIN_ACTION',
    'EVIDENCE_ACCESSED',
    'EXPORT_GENERATED',
    'ANCHOR_SUBMISSION_FAILED'
);

CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID
        REFERENCES organizations(id)
        ON DELETE SET NULL,             -- login attempts may not have an org

    event_type audit_event_type NOT NULL,
    user_id UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,
    subject_user_id UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    ip INET,
    user_agent TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX audit_events_org_time_idx
    ON audit_events (organization_id, created_at DESC);
CREATE INDEX audit_events_user_time_idx
    ON audit_events (user_id, created_at DESC);
