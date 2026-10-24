from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["Application Information"])


@router.get("/info")
def application_info() -> dict[str, str]:
    settings = get_settings()

    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "status": "running",
    }