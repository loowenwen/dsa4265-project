from fastapi import APIRouter

from app.api.v1.process import router as process_router
from app.api.v1.explain import router as explain_router

router = APIRouter()

router.include_router(process_router, tags=["process"])
router.include_router(explain_router, tags=["explain"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}