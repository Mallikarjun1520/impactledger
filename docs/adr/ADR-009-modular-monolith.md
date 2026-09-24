# ADR-009 — Modular monolith

Status: Accepted
Date: 2026-09-24

## Context

Microservices at MVP scale trade a manageable in-process codebase for a
distributed systems problem: network partitions between what should be one
transaction, duplicate schemas, deployment orchestration, and an operational
tax the team cannot afford.

## Decision

`apps/api` is a single FastAPI application organized by domain module:

```
apps/api/app/
  api/v1/              # HTTP routers, one per aggregate
  core/                # auth, config, exceptions, authorization
  domain/              # invariants, hashing, event definitions
  services/            # merkle, anchor adapter, ocr, llm
  infrastructure/      # DB access, external adapters
```

Modules do not import from each other's `infrastructure/` submodule directly;
they call the domain / service layer.

## Reason

Rulebook §25. One process, one deploy, one database transaction boundary,
easier free-tier hosting.

## Consequences

- Easier: consistency, tracing, deployment.
- Harder: horizontal scaling requires either shared DB (fine) or extracting
  a hot module. Not a near-term concern.

## Revisit conditions

If anchor workload or OCR pipeline blocks the request loop, promote them to
a scheduled worker (still one deployable, `apps/api/app/workers/`) before
considering extraction.
