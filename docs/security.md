# ImpactLedger — Security Model

## Trust boundaries

1. **Browser** — untrusted. Never authoritative for organization scope, role,
   or invariants. Sends a Supabase JWT bearer with every API call.
2. **Next.js server** — untrusted from the API's perspective. Convenience layer
   for SSR + Supabase client-side auth. Does not hold the service-role key.
3. **FastAPI monolith** — the sole authority for domain operations. Verifies
   the JWT (`SUPABASE_JWT_SECRET`) and resolves organization membership on
   every request via `apps/api/app/core/authorization.py`.
4. **Supabase Postgres** — second line of defense. RLS policies (migration
   `021_rls_policies.sql`) enforce tenant isolation independently of the API;
   migration `024_audit_events_role_rls.sql` restricts raw audit reads to
   organization admins and auditors. Legacy `audit_logs` history is copied
   into `audit_events` and the legacy table is retained for service-role use.
5. **Blockchain (Base Sepolia)** — integrity anchor only. No PII on-chain,
   ever. See ADR-007.

## Authentication

- Supabase Auth handles email/password sign-in and issues JWTs.
- WebAuthn/passkey option: `apps/web` uses `@simplewebauthn/browser`; server
  registration/attestation lives in `apps/api/app/api/v1/webauthn.py` in
  slice 2. Passkey credentials are stored in a `user_credentials` table
  scoped to `auth.users`, not to any organization.
- The passkey belongs to the human, not the role (rulebook §16). Organization
  membership and role attach separately.

## Authorization

- Two-layer: API + RLS. Every mutating endpoint calls a
  `require_role(org_id, roles)` dependency that resolves the caller's
  membership row. The DB then also enforces `organization_id = current_org()`
  in RLS.
- Segregation of duties: the `pO_approve` action rejects when
  `approved_by = created_by` unless the org policy explicitly permits it.

## Data classification

| Class                       | Storage                              | On-chain? |
|-----------------------------|--------------------------------------|-----------|
| Aggregated public totals    | Postgres view `public_initiative_*`  | Never     |
| Individual event content    | `domain_events.canonical_json`       | Never     |
| Event hash                  | `domain_events.hash`                 | Via Merkle root only |
| Evidence file bytes         | Supabase Storage private bucket      | Never     |
| Evidence file SHA-256       | `evidence.content_sha256`            | Optionally via Merkle root |
| Bank / donor PII            | `contributions.contributor_metadata` (JSONB, RLS locked) | Never |
| Audit events (login, denial)| `audit_events`                       | Never     |

## Non-negotiable rules (see rulebook §30)

1. No frontend-defined security boundaries.
2. No LLM in the authorization or approval path.
3. No PII on-chain.
4. No mutation of committed domain events.
5. No hiding of reconciliation discrepancies.

## Secret management

- All secrets injected via environment variables. `.env.example` at the repo
  root enumerates every required key. `.env` files are gitignored.
- Blockchain deployer key stored as a GitHub Actions secret
  (`ANCHOR_DEPLOYER_PRIVATE_KEY`) used only for the deploy workflow. The
  runtime anchoring key (`ANCHOR_RUNTIME_PRIVATE_KEY`) is a separate key held
  by the backend host with a small faucet balance.
- Supabase service-role key is used exclusively by the FastAPI service, never
  shipped to the browser.

## Auditability

- Every state change writes a `domain_events` row inside the same DB
  transaction as the operational insert. The event's `canonical_json` is the
  authoritative record.
- Auditors get a role that grants SELECT on `domain_events`,
  `provenance_edges`, `evidence` metadata (not bytes), and full read on
  `audit_events`. No write permissions.
