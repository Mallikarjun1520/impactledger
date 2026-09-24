# ADR-005 — LLM cannot make authoritative decisions

Status: Accepted
Date: 2026-09-24

## Context

LLMs are helpful for extracting fields from an invoice, mapping natural
language to candidate events, summarizing a reconciliation report. They are
non-deterministic, occasionally wrong, and cannot be audited the way a
deterministic rule can.

## Decision

LLM outputs are always advisory candidates that a human must confirm.
LLMs cannot:

- approve any transaction
- authorize a user
- decide balance authoritativeness
- accept or reject evidence
- override any invariant

The `apps/api/app/services/llm.py` interface exposes only
`extract_candidates`, `explain`, and `summarize`. There is no
`approve` method — by design.

## Reason

- Rulebook Rule 02, Rule 03, Rule 09.
- Determinism is auditable; probabilistic decisions are not.

## Consequences

- Easier: passing regulatory scrutiny, aligning with the transparency claim,
  gracefully degrading when the LLM is unavailable.
- Harder: some workflows require a human loop even when an LLM could nudge
  them faster. Acceptable trade.

## Revisit conditions

Never for authoritative decisions. Advisory scope may expand.
