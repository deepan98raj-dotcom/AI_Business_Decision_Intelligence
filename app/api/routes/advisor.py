
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.advisor_service import (
    AdvisorConfigurationError,
    AdvisorDataError,
    generate_executive_advice,
)

router = APIRouter(
    prefix="/advisor",
    tags=["Executive AI Advisor"],
)


class AdvisorQuestion(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Business question for the executive advisor",
        examples=[
            "How can we improve Hyderabad profitability "
            "and Enterprise customer satisfaction?"
        ],
    )


@router.get("/health")
def advisor_health():
    """Check whether the advisor endpoint is registered."""
    return {
        "status": "ok",
        "service": "groq-executive-advisor",
        "provider": "groq",
    }


@router.post("/ask")
def ask_executive_advisor(payload: AdvisorQuestion):
    """Generate a business report from existing analytics."""
    try:
        return generate_executive_advice(payload.question.strip())

    except AdvisorDataError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except AdvisorConfigurationError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
