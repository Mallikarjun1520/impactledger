# ImpactLedger — Implementation Plan

This plan realizes the rulebook (`IMPACTLEDGER_RULEBOOK_v1.0.md`) in eight
build slices. Each slice is independently testable and produces a demonstrable
outcome from the rulebook's §28 canonical scenarios.

## Slice 0 — Freeze artifacts (this delivery)

- ERD: `docs/architecture/erd.md`
- ADR-001…ADR-015: `docs/adr/`
- Security notes: `docs/security.md`
- Deployment: `docs/deployment.md`
- Implementation plan: this file

## Slice 1 — Domain foundations (this delivery)

- Migrations 011–022 add: initiatives, fund_pools, contribution restrictions,
  vendors, commitments, purchase_orders, payments, evidence, evidence_links,
  domain_events (with per-org hash chain), provenance_edges, audit_events,
  anchor_batches, anchor_batch_items, RLS policies, public views, seed data.
- Backend: `apps/api/app/domain/{events,invariants,hashing,validation}.py`,
  `apps/api/app/services/{merkle,anchor,anchor_evm,anchor_noop,ocr,llm}.py`,
  and routers for every new module.
- Solidity: `packages/contracts/contracts/ImpactAnchor.sol` + Hardhat config,
  tests, and Base Sepolia deploy script.
- Infra: `infra/docker-compose.yml`, backend + web `Dockerfile`s, GitHub Actions
  CI workflow (Python + Node + Solidity).

## Slice 2 — Vertical: emergency micro-donations (scenario 1)

Realizes scenario §28.1 end-to-end:

1. `POST /api/v1/contributions` records small contributions and aggregates them
   into a compatible `fund_pools` row.
2. `POST /api/v1/allocations` draws from the pool; deterministic invariants
   enforce cap.
3. `POST /api/v1/anchor/batches` closes a Merkle batch, computes root,
   dispatches to the EVM adapter.
4. `GET /public/{org}/{initiative}` renders the sanitized projection with the
   Merkle proof verification widget.

Frontend deliverables:

- Contributor onboarding (Supabase Auth email or passkey via `@simplewebauthn`)
- Org switcher
- Contribute-to-pool form with visibility selector
- Allocation form
- Public transparency page + client-side Merkle verifier

## Slice 3 — Restricted funds & purpose enforcement (scenario 2)

- Contribution restriction JSON schema: `{ scope: "unrestricted"|"initiative"|"category", initiative_id?, category? }`.
- Allocation validator rejects transfers to non-permitted scopes deterministically.
- Public page shows restricted balance broken out separately.

## Slice 4 — Procurement + physical linkage (scenarios 3, 5, 6)

- Commitment → PO → Payment path with segregation-of-duties check.
- Receipt event on PO creates a `resource_batches` row.
- Physical event ledger enforces conservation (§8) with a `resource_movements`
  invariant checker.
- Discrepancy events surface on both public and internal reconciliation views.

## Slice 5 — Evidence + OCR + LLM assist (scenarios 4, 10, 11, 12)

- Upload → Storage (`org/{org_id}/evidence/{evidence_id}`) with server-side
  `sha256`.
- OCR pipeline (async worker; Tesseract in-image via pytesseract or an
  external free-tier API behind the `OcrProvider` interface).
- LLM extraction narrows candidate events; user must approve. Manual fallback
  route always available.
- Missing / mismatched evidence → `NEEDS_REVIEW` status; nothing silently
  auto-approves.

## Slice 6 — Corrections, reversals, self-approval (scenarios 7, 8, 9)

- `POST /api/v1/events/{id}/correct` and `/reverse` add new events with the
  proper provenance edges; never mutate the original.
- Self-approval: `PO_APPROVE` blocked when `approved_by = created_by` unless
  an org policy explicitly disables the check.

## Slice 7 — Public verification (scenario 14)

- Client fetches record hash + Merkle proof + on-chain anchor.
- Verifies proof locally in-browser, then reads the on-chain root from Base
  Sepolia via `viem` and compares.
- "Verified ✅" or "Anchor pending" surfaces to the public.

## Slice 8 — Organization suspension & closure (scenarios 13, 15)

- Anchor-outage handling: events remain committed with
  `anchor_status = 'PENDING'`; a background scheduler retries.
- Suspension blocks INSERTs into operational tables via RLS predicate;
  historical rows remain fully readable to auditors.

## Test matrix

| Layer          | Tool            | Scope                                            |
|----------------|-----------------|--------------------------------------------------|
| SQL policies   | pgTAP (`supabase/tests/`) | RLS visibility, cross-tenant negative cases |
| Domain         | pytest          | Invariants, hashing determinism, Merkle round-trip |
| Router         | pytest+httpx    | Membership enforcement, restriction enforcement  |
| Solidity       | Hardhat + chai  | Anchor accept/reject, event emission             |
| End-to-end     | Playwright      | Contribution → allocation → anchor → public page |

## $0 deployment topology

- Frontend: Vercel free tier (Next.js).
- Backend: Fly.io free 256MB VM or Render free web service (FastAPI).
- Database + Auth + Storage: Supabase free tier.
- Blockchain: Base Sepolia public testnet; anchor gas paid from a faucet-funded key.
- CI: GitHub Actions free tier.

## Definition of done per slice

1. New routes have Pydantic request/response models with examples.
2. Every operational INSERT paired with a `domain_events` write in the same transaction.
3. Every new tenant-owned table has an RLS policy and a negative pgTAP test.
4. Every rulebook invariant added has a positive and negative unit test.
5. Every scenario in §28 the slice claims has a Playwright test.
