from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.api.v1.distributions import router as distributions_router

app = FastAPI(
    title="ImpactLedger API",
    version="0.1.0",
)

app.include_router(
    health_router,
    prefix="/api/v1",
)

app.include_router(
    distributions_router,
    prefix="/api/v1",
)