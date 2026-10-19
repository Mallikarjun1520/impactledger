-- Rulebook §17/§18 security hardening (forward-only follow-up to 021).
--
-- domain_event_sequences stores the per-organization (last_seq, last_hash)
-- state used to chain domain_events (migration 017). Migration 021 enabled
-- RLS on 22 operational tables but omitted this support table, so Supabase's
-- default Data-API grants left it readable and writable to anon/authenticated
-- through PostgREST. That allowed tampering with the local hash-chain state.
--
-- This migration does not edit any applied migration. It:
--   * enables and forces RLS on the table (no anon/authenticated policy),
--   * removes the default Data-API grants as defence in depth,
--   * preserves backend access (the API connects as the table owner, which
--     has BYPASSRLS) and a service_role policy for PostgREST service clients.

ALTER TABLE domain_event_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_event_sequences FORCE ROW LEVEL SECURITY;

REVOKE ALL ON domain_event_sequences FROM anon, authenticated;

CREATE POLICY domain_event_sequences_service_role ON domain_event_sequences
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);
