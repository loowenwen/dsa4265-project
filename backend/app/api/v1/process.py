from fastapi import APIRouter, HTTPException

from app.models.schemas import ProcessRequest, ProcessResponse
from app.services.adapters.form_adapter import FormInputAdapter
from app.services.pipeline import build_process_response

router = APIRouter()


@router.post("/process", response_model=ProcessResponse)
def process_applicant(payload: ProcessRequest) -> ProcessResponse:
    adapter = FormInputAdapter()
    parsed, errors = adapter.adapt(payload)

    if errors:
        raise HTTPException(status_code=422, detail=errors)

    return build_process_response(parsed)
