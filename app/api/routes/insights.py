
# app/api/routes/insights.py

import logging

from fastapi import APIRouter, HTTPException

from app.services.insight_service import generate_executive_insights

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/insights",
    tags=["Executive Decision Intelligence"],
)


@router.get("/executive")
def executive_insights():
    """Generate executive KPIs, business insights, and recommendations."""

    try:
        return generate_executive_insights()

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Failed to generate executive insights")
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate executive insights. "
                "Check the application logs."
            ),
        ) from exc
