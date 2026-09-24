# ADR-015 — Sanitized public transparency

Status: Accepted
Date: 2026-09-24

## Context

Rulebook §19 requires public transparency, but naive exposure of the
operational tables leaks PII (donor details, beneficiary identity, bank
information), operational secrets (vendor pricing), and creates a real
harm vector. Simultaneously, transparency must not hide discrepancies to
make an org look better.

## Decision

The public surface is a set of read-only Postgres views (migration `021`)
that:

- Aggregate contributions to totals + anonymized counts unless the donor
  chose `visibility = 'PUBLIC'`.
- Expose allocations by purpose, not by individual instrument.
- Publish reconciliation *status and variance*, never omitted.
- Serve evidence *metadata + hash* only. Bytes require an authenticated
  signed URL from the backend.
- Never expose bank details, contact info, or internal notes.

The Next.js public route (`/public/[org]/[initiative]`) reads only these
views via the anon Supabase key.

## Reason

Rulebook Rule 08, Rule 18, §19. Views enforce the projection at the DB
level so a bug in a route cannot leak private columns.

## Consequences

- Easier: safe defaults, single place to audit projection.
- Harder: adding a new public field requires a view change + migration.
  This friction is a feature.

## Revisit conditions

Any request to add a public field triggers a security review + this ADR is
updated.
