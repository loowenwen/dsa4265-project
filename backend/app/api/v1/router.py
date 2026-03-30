from fastapi import APIRouter

from app.api.v1.process import router as process_router

router = APIRouter()
router.include_router(process_router)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
