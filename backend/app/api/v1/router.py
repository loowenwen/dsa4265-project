from fastapi import APIRouter

from app.api.v1.process import router as process_router
from app.api.v1.explain import router as explain_router
from app.services.modeling import providers

router = APIRouter()

router.include_router(process_router, tags=["process"])
router.include_router(explain_router, tags=["explain"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/models")
def health_models() -> dict[str, object]:
    return providers.get_model_readiness()
