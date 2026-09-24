# ADR-008 — Redis excluded

Status: Accepted
Date: 2026-09-24

## Context

Redis is the default reflex answer to "we need a cache / queue / lock." For
MVP scale, it is unnecessary infrastructure that:

- adds a container, a network hop, and an environment secret;
- consumes free-tier budget (rulebook §24);
- introduces a source of state divergence from Postgres.

## Decision

Redis is intentionally excluded. Ordinary Postgres serves for:

- Idempotency keys (unique constraints on request ids).
- Anchor batching (a scheduled job scans `domain_events` for `anchor_status =
  'PENDING'` and closes a batch).
- Rate limits (edge-level via Vercel / Fly.io).
- Session storage (Supabase Auth handles this).

## Reason

Rulebook Rule 10, §24 $0 constraint, principle of minimum viable
infrastructure.

## Consequences

- Easier: fewer moving parts, cheaper.
- Harder: high-concurrency workloads would need to add a queue eventually.
  Acceptable trade for MVP.

## Revisit conditions

Sustained > 100 rps write load, or a documented feature that genuinely
requires a distributed lock.
