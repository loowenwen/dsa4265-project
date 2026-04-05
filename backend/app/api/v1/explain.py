from fastapi import APIRouter
from app.models.schemas import ExplanationRequest, ExplanationResponse
from app.services.explainer import build_explanation

router = APIRouter()

@router.post("/explain", response_model=ExplanationResponse)
def explain_application(payload: ExplanationRequest) -> ExplanationResponse:
    return build_explanation(payload)