from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    DataQuality,
    OrchestratorInput,
    ProcessRequest,
    ProcessResponse,
    PolicySupport,
    ExplanationMemo,
)
from app.services.adapters.form_adapter import FormInputAdapter
from app.services.pipeline import build_process_response
from app.services import providers
from app.services.decision_engine import run_dual_engine

router = APIRouter()


@router.post("/process", response_model=ProcessResponse)
def process_applicant(payload: ProcessRequest) -> ProcessResponse:
    adapter = FormInputAdapter()
    parsed, errors = adapter.adapt(payload)

    if errors:
        raise HTTPException(status_code=422, detail=errors)

    base_response = build_process_response(parsed)

    default_output = providers.get_default_model_output(base_response.feature_vector)
    anomaly_output = providers.get_anomaly_model_output(base_response.feature_vector)
    policy_output = providers.get_policy_retrieval_output(base_response.feature_vector)

    data_quality = DataQuality(
        missing_required_fields=base_response.missing_fields,
        suspicious_fields=[item.field for item in base_response.suspicious_fields] or [],
        parse_warnings=None,
        is_complete=len(base_response.missing_fields) == 0,
    )

    # New dual decision engine
    rule_decision, ai_decision, alignment = run_dual_engine(
        applicant=base_response.feature_vector.model_dump()
        if hasattr(base_response.feature_vector, "model_dump")
        else base_response.feature_vector.__dict__,
        default_probability=default_output.default_probability,
        anomaly_score=anomaly_output.anomaly_score,
        missing_fields=base_response.missing_fields,
        suspicious_fields=[item.field for item in base_response.suspicious_fields] or [],
        policy_output=policy_output,
    )

    policy_support = PolicySupport(
        available=bool(policy_output and policy_output.retrieved_rules),
        snippets=[r.snippet for r in policy_output.retrieved_rules] if policy_output and policy_output.retrieved_rules else [],
    )

    explanation_memo = ExplanationMemo(
        memo="Dual decisions synthesized.",
        summary=None,
    )

    base_response.default_model_output = default_output
    base_response.anomaly_model_output = anomaly_output
    base_response.policy_retrieval_output = policy_output
    base_response.orchestrator_output = None
    base_response.rule_decision = rule_decision
    base_response.ai_decision = ai_decision
    base_response.decision_alignment = alignment
    base_response.policy_support = policy_support
    base_response.explanation = explanation_memo

    return base_response
