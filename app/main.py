from contextlib import asynccontextmanager
import logging
from app.api.routes import ingestion
from fastapi import FastAPI
from app.api.routes import insights
from app.api.routes import analytics
from app.api.routes import health, info
from app.api.routes import advisor, analytics, insights
from app.core.config import get_settings
from app.core.logging_config import configure_logging

settings = get_settings()
configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.app_name)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "An AI-powered platform for business performance analysis, "
        "executive decision support, and strategic recommendations."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)
app.include_router(
    advisor.router,
    prefix=settings.api_v1_prefix)
app.include_router(
    insights.router,
    prefix=settings.api_v1_prefix,
)
app.include_router(
    analytics.router,
    prefix=settings.api_v1_prefix,
)
app.include_router(health.router)
app.include_router(
    info.router,
    prefix=settings.api_v1_prefix,
)
app.include_router(
    ingestion.router,
    prefix=settings.api_v1_prefix,
)


@app.get("/", tags=["General"])
def root() -> dict[str, str]:
    return {
        "message": "Welcome to the AI Business Decision Intelligence Platform",
        "docs": "/docs",
        "health": "/health",
        "info": f"{settings.api_v1_prefix}/info",
    }
    