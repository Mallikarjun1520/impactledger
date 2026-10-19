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

-- Preserve historical legacy audit rows in the canonical event stream.
INSERT INTO audit_events (
    organization_id, event_type, user_id, details, created_at
)
SELECT
    legacy.organization_id,
    'ADMIN_ACTION',
    legacy.actor_id,
    jsonb_build_object(
        'action', legacy.action,
        'entity_type', legacy.entity_type,
        'entity_id', legacy.entity_id::text,
        'metadata', COALESCE(legacy.metadata, '{}'::jsonb),
        'legacy_audit_log_id', legacy.id::text
    ),
    legacy.timestamp
FROM audit_logs AS legacy
WHERE NOT EXISTS (
    SELECT 1
    FROM audit_events AS existing
    WHERE existing.details->>'legacy_audit_log_id' = legacy.id::text
);

CREATE INDEX audit_events_org_time_idx
    ON audit_events (organization_id, created_at DESC);
CREATE INDEX audit_events_user_time_idx
    ON audit_events (user_id, created_at DESC);
