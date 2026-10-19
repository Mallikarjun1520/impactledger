# ImpactLedger — Deployment

Meets the rulebook §24 constraint: **$0 demo**.

## Local development

```bash
# 1. Copy env template
cp .env.example .env

# 2. Start Supabase locally (Docker required)
cd supabase && supabase start && cd ..

# 3. Backend
cd apps/api
python -m venv .venv && . .venv/Scripts/activate  # or .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000

# 4. Frontend
cd ../web
npm install
npm run dev  # http://localhost:3000

# 5. Contracts
cd ../../packages/contracts
npm install
npx hardhat test
```

Before starting FastAPI for local development, set `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, and
`DATABASE_URL` from the local `supabase status -o env` output. Confirm that the
Supabase API is on loopback port 54321 and PostgreSQL is on loopback port 54322;
process environment values override `apps/api/.env`, which may contain hosted
deployment settings.

### Local development without Docker log collection

Supabase's optional `vector` and `logflare` services collect container logs
through the Docker Engine API; they are not required for the database, Auth,
Storage, API, or frontend. On Docker Desktop installations that expose the
Engine only through a named pipe, Vector's configured
`host.docker.internal:2375` TCP endpoint is unavailable. Start the required
services without the optional log collector using the Supabase CLI's supported
exclude flag:

```bash
npm exec -- supabase start --exclude vector,logflare
```

### Live database RLS integration tests

These tests connect to and exercise policies in the local Supabase PostgreSQL
instance. They skip unless the dedicated test URL is set; they reject any
database URL that is not the local loopback endpoint on port 54322. Each test
uses isolated rows and rolls them back. The relief-lifecycle test exercises
FastAPI routes against that same database inside one rollback transaction.

```bash
# Start local Supabase first, then from the repository root:
cd apps/api
# PowerShell:
$env:IMPACTLEDGER_RLS_TEST_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
$env:IMPACTLEDGER_LIFECYCLE_TEST_DATABASE_URL = $env:IMPACTLEDGER_RLS_TEST_DATABASE_URL
python -m pytest -q tests/test_rls_integration.py tests/test_relief_lifecycle_integration.py
```

Or with docker-compose from repo root:

```bash
docker-compose -f infra/docker-compose.yml up --build
```

## Production ($0)

| Layer      | Service            | Notes                                                             |
|------------|--------------------|-------------------------------------------------------------------|
| Frontend   | Vercel free tier   | Next.js. Env vars set in Vercel dashboard.                        |
| Backend    | Fly.io shared-cpu-1x free VM | 256MB Dockerfile in `apps/api/Dockerfile`.             |
| DB/Auth    | Supabase free      | Migrations applied via `supabase db push`.                        |
| Storage    | Supabase Storage   | Private bucket `evidence`.                                        |
| Anchor RPC | Public Base Sepolia RPC | `https://sepolia.base.org` (rate-limited; fall back to Ankr free tier). |
| Gas        | Base Sepolia faucet | `https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet`. |
| CI         | GitHub Actions free | `.github/workflows/ci.yml`.                                       |

## Environment variables (root `.env.example`)

```
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=

# Backend
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
APP_ENV=development

# Frontend
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Blockchain (anchor)
ANCHOR_CHAIN_ID=84532                       # Base Sepolia
ANCHOR_RPC_URL=https://sepolia.base.org
ANCHOR_CONTRACT_ADDRESS=                    # populated after deploy
ANCHOR_RUNTIME_PRIVATE_KEY=                 # small faucet-funded key
ANCHOR_ADAPTER=evm                          # 'evm' or 'noop'

# OCR / LLM (interfaces; leave blank to use noop provider)
OCR_PROVIDER=noop
LLM_PROVIDER=noop
```

## Deploy runbook

1. Push to `main` → GitHub Actions runs full test matrix.
2. If green, GitHub Actions workflow `deploy-contracts.yml` (manual dispatch)
   deploys `ImpactAnchor.sol` to Base Sepolia and writes the address to a
   repo secret.
3. Vercel auto-deploys `apps/web` on `main`.
4. Fly.io deploys `apps/api` on `main` via `flyctl deploy --remote-only`
   (see `infra/fly.toml.example`).
5. First run: apply migrations with `supabase db push --linked` (project
   already linked in `supabase/config.toml`).

## Rollback

- Frontend: Vercel one-click revert.
- Backend: `flyctl releases rollback`.
- DB: forward-only migrations. Rollback ⇒ new migration that inverts. **Never**
  drop or edit an old migration file.
- Contracts: redeploy; the old contract remains on-chain (rulebook §22 —
  blockchain state is immutable). Cutover happens by updating
  `ANCHOR_CONTRACT_ADDRESS`; anchors written to the old address are still
  publicly verifiable there.
