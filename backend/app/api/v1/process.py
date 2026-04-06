from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    DataQuality,
    OrchestratorInput,
    ProcessRequest,
    ProcessResponse,
)
from app.services.adapters.form_adapter import FormInputAdapter
from app.services.orchestrator import decide
from app.services.pipeline import build_process_response
from app.services import providers

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

    orchestrator_input = OrchestratorInput(
        applicant=base_response.feature_vector.model_dump()
        if hasattr(base_response.feature_vector, "model_dump")
        else base_response.feature_vector.__dict__,
        risk=default_output,
        anomaly=anomaly_output,
        policy=policy_output,
        data_quality=data_quality,
    )

    orchestration = decide(orchestrator_input)

    base_response.default_model_output = default_output
    base_response.anomaly_model_output = anomaly_output
    base_response.policy_retrieval_output = policy_output
    base_response.orchestrator_output = orchestration

    return base_response
