# ImpactLedger

ImpactLedger tracks and verifies the recorded lifecycle of funds and resources.

## Project

ImpactLedger is a transparency and provenance platform designed to help organizations record the lifecycle of financial contributions, procurement activities, physical resources, and distribution events.

## Architecture

- Frontend: Next.js + TypeScript
- Backend: FastAPI + Python
- Database: Supabase PostgreSQL
- Authentication: Supabase Auth + Passkeys
- Storage: Supabase Storage
- Blockchain: EVM testnet for cryptographic anchoring
- LLM: User interaction and intent interpretation only

## Repository Structure

- `apps/web` — Next.js frontend
- `apps/api` — FastAPI backend
- `packages` — shared packages and contracts
- `infra` — infrastructure and database migrations
- `docs` — architecture, ADRs, API documentation, and project rules
- `tests` — project-level tests

## Development Status

🚧 Initial project scaffolding