from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.anchor import router as anchor_router
from app.api.v1.auth import router as auth_router
from app.api.v1.distributions import router as distributions_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.fund_pools import router as fund_pools_router
from app.api.v1.health import router as health_router
from app.api.v1.initiatives import router as initiatives_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.procurement import router as procurement_router
from app.api.v1.public import router as public_router


app = FastAPI(
    title="ImpactLedger API",
    version="0.2.0",
    description=(
        "ImpactLedger — modular monolith realizing IMPACTLEDGER_RULEBOOK_v1.0.\n\n"
        "Two-layer authorization (backend + Postgres RLS). Immutable domain "
        "events with per-org SHA-256 hash chain. Merkle batch anchoring on "
        "Base Sepolia via a swappable adapter."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                   # local dev; tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

for r in (
    health_router,
    auth_router,
    organizations_router,
    initiatives_router,
    fund_pools_router,
    procurement_router,
    distributions_router,
    evidence_router,
    anchor_router,
    public_router,
):
    app.include_router(r, prefix="/api/v1")
