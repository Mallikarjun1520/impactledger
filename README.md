# ImpactLedger

ImpactLedger tracks and verifies the recorded lifecycle of funds and resources.

Source of truth: [`../IMPACTLEDGER_RULEBOOK_v1.0.md`](../IMPACTLEDGER_RULEBOOK_v1.0.md).

## What this is

A multi-tenant transparency and provenance platform. Donors and auditors can
see what was recorded, how the records connect, the evidence supporting
them, the discrepancies the system found, and the cryptographic proof that
the recorded history has not been silently rewritten.

## Architecture

- **Frontend:** Next.js 16 + TypeScript ([apps/web](apps/web))
- **Backend:** FastAPI modular monolith ([apps/api](apps/api))
- **Database + Auth + Storage:** Supabase PostgreSQL 17 ([supabase](supabase))
- **Blockchain anchor:** Base Sepolia via a swappable EVM adapter ([packages/contracts](packages/contracts))
- **Deploy:** $0 free-tier topology (Vercel + Fly.io + Supabase free)

## Repository map

```
apps/api                 FastAPI monolith
apps/web                 Next.js frontend
packages/contracts       Solidity anchor contract + Hardhat
supabase/                Postgres migrations, seed, config
docs/                    ERD, ADRs, implementation plan, security, deployment
infra/                   Docker + deploy
.github/workflows/       CI (Python + Node + Solidity)
```

## Quick start

See [docs/deployment.md](docs/deployment.md) for the full runbook.

```bash
# 1. Env
cp .env.example .env    # fill Supabase keys

# 2. Backend (pure-domain tests, no DB required)
cd apps/api
pip install -e .[dev]
pytest -q tests/test_hashing.py tests/test_merkle.py tests/test_invariants.py

# 3. Anchor contract
cd ../../packages/contracts
npm install
npx hardhat test

# 4. Frontend
cd ../../apps/web
npm install
npm run dev
```

Or use the Makefile targets: `make api-test contracts-test web-dev`.

## Documents

- [ERD](docs/architecture/erd.md)
- [Implementation plan](docs/implementation-plan.md)
- [Security model](docs/security.md)
- [Deployment](docs/deployment.md)
- ADRs 001–015 in [docs/adr/](docs/adr/)

## Rulebook alignment

Every migration, module, and ADR cites the rulebook rule or section it
realizes. Non-negotiable rules (§30) are enforced at the database level with
triggers and RLS, and in the application with pure invariant checks in
[apps/api/app/domain/invariants.py](apps/api/app/domain/invariants.py).
