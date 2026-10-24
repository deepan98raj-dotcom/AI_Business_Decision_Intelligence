
# app/api/routes/analytics.py

from fastapi import APIRouter, HTTPException, Query

from app.services.analytics_service import (
    get_feedback_analytics,
    get_sales_analytics,
)

router = APIRouter(
    prefix="/analytics",
    tags=["Business Analytics"],
)


def _run_analytics(function, filename: str | None):
    try:
        return function(filename=filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Keep implementation details out of the public API response.
        raise HTTPException(
            status_code=500,
            detail="Analytics calculation failed. Check the application logs.",
        ) from exc


@router.get("/sales")
def sales_analytics(
    filename: str | None = Query(
        default=None,
        description=(
            "Optional processed sales CSV filename. "
            "If omitted, the newest matching file is selected."
        ),
    ),
):
    """Return sales KPIs, regional/product performance, trends, and anomalies."""
    return _run_analytics(get_sales_analytics, filename)


@router.get("/feedback")
def feedback_analytics(
    filename: str | None = Query(
        default=None,
        description=(
            "Optional processed customer-feedback CSV filename. "
            "If omitted, the newest matching file is selected."
        ),
    ),
):
    """Return customer-rating and feedback-segment analytics."""
    return _run_analytics(get_feedback_analytics, filename)
