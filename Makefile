.PHONY: help api-install api-test api-run api-lint web-install web-dev web-build contracts-install contracts-test contracts-deploy db-start db-reset docker-up docker-down

help:
	@echo "Common targets:"
	@echo "  make api-install       Install FastAPI deps"
	@echo "  make api-test          Run pure-domain tests (no DB required)"
	@echo "  make api-run           uvicorn dev server"
	@echo "  make web-install       npm install for Next.js app"
	@echo "  make web-dev           next dev on :3000"
	@echo "  make contracts-test    Hardhat unit tests for ImpactAnchor"
	@echo "  make contracts-deploy  Deploy to Base Sepolia (needs env)"
	@echo "  make db-start          Start local Supabase (docker required)"
	@echo "  make db-reset          Reset local Supabase DB and apply migrations + seed"
	@echo "  make docker-up         Build + run api and web in Docker"

api-install:
	cd apps/api && pip install -e .[dev]

api-lint:
	cd apps/api && ruff check .

api-test:
	cd apps/api && pytest -q tests/test_hashing.py tests/test_merkle.py tests/test_invariants.py

api-run:
	cd apps/api && uvicorn app.main:app --reload --port 8000

web-install:
	cd apps/web && npm install --no-audit --no-fund

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build

contracts-install:
	cd packages/contracts && npm install --no-audit --no-fund

contracts-test:
	cd packages/contracts && npx hardhat test

contracts-deploy:
	cd packages/contracts && npx hardhat run scripts/deploy.js --network baseSepolia

db-start:
	cd supabase && supabase start

db-reset:
	cd supabase && supabase db reset

docker-up:
	docker compose -f infra/docker-compose.yml up --build

docker-down:
	docker compose -f infra/docker-compose.yml down
