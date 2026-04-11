from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat.chat_service import build_chat_response

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    return build_chat_response(payload)
