# ADR-014 — Supabase PostgreSQL

Status: Accepted
Date: 2026-09-24

## Context

We need a managed relational DB with strong integrity primitives, real Row
Level Security, first-class auth, storage, and a free tier. Rolling our own
Postgres+Keycloak+MinIO defeats the $0 constraint and doubles operational
work.

## Decision

Supabase (managed PostgreSQL 17). RLS is the second-layer enforcement of
tenant boundaries; the backend is the first layer.

## Reason

- Rulebook §17 explicitly calls for RLS.
- Supabase Auth issues JWTs the FastAPI backend can verify offline with
  `SUPABASE_JWT_SECRET`.
- Supabase Storage handles the evidence bucket, keeping bytes out of the DB.
- Free tier fits.

## Consequences

- Easier: auth + storage bundled.
- Harder: vendor lock-in. Mitigation: everything is standard Postgres +
  a JWT secret. Migrating to self-hosted Postgres + Keycloak is possible
  without an app rewrite; the auth layer only needs the JWT to keep the
  same claim shape.

## Revisit conditions

Supabase pricing change that breaks the $0 constraint, or a partner
requiring on-prem hosting.
