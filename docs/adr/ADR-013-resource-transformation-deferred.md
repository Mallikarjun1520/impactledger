# ADR-013 — Resource transformation deferred

Status: Accepted
Date: 2026-09-24

## Context

Real relief operations sometimes transform inputs into outputs: 100 kg of
rice → 800 food packets. Modelling this correctly needs an
input-batch → transformation-event → output-batch lineage that touches the
event schema, the invariant checker, and the public projection.

## Decision

Not in MVP. The rulebook §21 documents the future shape but implementation
is deferred. Current model treats a transformation as (a) a distribution of
the input batch and (b) a fresh receipt of the output batch, with an
optional free-text linkage note.

## Reason

Complexity does not justify the demo value. The freeze artifacts (§21)
reserve the concept so we don't paint ourselves into a corner.

## Consequences

- Easier: MVP delivery.
- Harder: transformation-heavy orgs will feel this. Acceptable for MVP;
  the future extension adds a `resource_transformations` table without
  breaking existing rows.

## Revisit conditions

A partner with materially transformational operations onboards, or the
public verifier UX needs transformation lineage.
