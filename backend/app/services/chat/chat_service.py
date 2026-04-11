from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock

import httpx

from app.core import settings
from app.models.schemas import ChatCitation, ChatMemoryState, ChatRequest, ChatResponse
from app.services.policy.rag_pipeline import answer_policy_query_fast


MAX_CITATIONS = 3
SNIPPET_MAX_CHARS = 240


@dataclass(slots=True)
class ChatSessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    expires_at: float = 0.0


_SESSION_LOCK = Lock()
_SESSIONS: dict[str, ChatSessionState] = {}


def _memory_turn_limit() -> int:
    return max(1, int(settings.CHAT_MEMORY_MAX_TURNS))


def _memory_ttl_seconds() -> int:
    return max(1, int(settings.CHAT_MEMORY_TTL_SECONDS))


def _cleanup_expired_sessions(now: float) -> None:
    expired_session_ids = [
        session_id
        for session_id, state in _SESSIONS.items()
        if state.expires_at <= now
    ]
    for session_id in expired_session_ids:
        del _SESSIONS[session_id]


def _get_or_create_session(session_id: str | None) -> tuple[str, list[dict[str, str]]]:
    now = time.time()
    ttl = _memory_ttl_seconds()
    resolved_session_id = session_id or str(uuid.uuid4())

    with _SESSION_LOCK:
        _cleanup_expired_sessions(now)

        state = _SESSIONS.get(resolved_session_id)
        if state is None:
            state = ChatSessionState(messages=[], expires_at=now + ttl)
            _SESSIONS[resolved_session_id] = state
        else:
            state.expires_at = now + ttl

        prior_messages = [dict(message) for message in state.messages]

    return resolved_session_id, prior_messages


def _append_turn(session_id: str, user_message: str, assistant_message: str) -> ChatMemoryState:
    now = time.time()
    ttl = _memory_ttl_seconds()
    turn_limit = _memory_turn_limit()

    with _SESSION_LOCK:
        _cleanup_expired_sessions(now)

        state = _SESSIONS.get(session_id)
        if state is None:
            state = ChatSessionState(messages=[], expires_at=now + ttl)
            _SESSIONS[session_id] = state

        state.messages.append({"role": "user", "content": user_message})
        state.messages.append({"role": "assistant", "content": assistant_message})

        truncated = False
        while len(state.messages) > (turn_limit * 2):
            truncated = True
            del state.messages[:2]

        state.expires_at = now + ttl

        return ChatMemoryState(
            turn_count=len(state.messages) // 2,
            truncated=truncated,
        )


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clip_text(value: str, limit: int) -> str:
    normalized = _normalize_whitespace(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _build_citations(rag_result: dict) -> list[ChatCitation]:
    citations: list[ChatCitation] = []
    for item in (rag_result.get("reranked_docs") or [])[:MAX_CITATIONS]:
        chunk_id = str(item.get("chunk_id") or "unknown")
        title = str(item.get("title") or "Untitled policy chunk")
        section_header = str(item.get("section_header") or "Unknown section")
        snippet = _clip_text(str(item.get("text") or ""), SNIPPET_MAX_CHARS)
        if not snippet:
            snippet = f"Policy reference: {chunk_id}."

        citations.append(
            ChatCitation(
                chunk_id=chunk_id,
                title=title,
                section_header=section_header,
                snippet=snippet,
            )
        )
    return citations


def _format_memory_context(messages: list[dict[str, str]]) -> str:
    if not messages:
        return "No prior conversation."

    lines: list[str] = []
    for message in messages[-(_memory_turn_limit() * 2) :]:
        role = "User" if message.get("role") == "user" else "Assistant"
        content = _clip_text(str(message.get("content") or ""), 400)
        if content:
            lines.append(f"{role}: {content}")

    if not lines:
        return "No prior conversation."

    return "\n".join(lines)


def _extract_response_text(response_json: dict) -> str:
    choices = response_json.get("choices", [])
    for choice in choices:
        message = choice.get("message", {})
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        chunks.append(text)
            merged = "".join(chunks).strip()
            if merged:
                return merged

    raise ValueError("No output text returned by OpenRouter chat model.")


def _serialize_decision_context(payload: ChatRequest) -> str:
    if payload.decision_payload is None:
        return "Not provided."

    compact = json.dumps(payload.decision_payload.model_dump(), ensure_ascii=False)
    return _clip_text(compact, 5000)


def _build_chat_messages(
    payload: ChatRequest,
    memory_context: str,
    retrieval_context: str,
    citation_ids: list[str],
) -> list[dict[str, str]]:
    citation_list = ", ".join(citation_ids) if citation_ids else "none"
    decision_context = _serialize_decision_context(payload)

    system_prompt = (
        "You are a financial underwriting policy assistant. "
        "Answer only from the retrieved policy context and optional decision context. "
        "Do not invent policies, thresholds, or facts. "
        "If context is insufficient, say so clearly. "
        "Keep responses concise and practical."
    )

    user_prompt = (
        f"Conversation memory:\n{memory_context}\n\n"
        f"Retrieved policy context:\n{retrieval_context or 'No retrieval context available.'}\n\n"
        f"Latest applicant decision context:\n{decision_context}\n\n"
        f"User question:\n{payload.message}\n\n"
        "Output requirements:\n"
        "1. Provide a direct answer first.\n"
        "2. Keep recommendations grounded in provided evidence only.\n"
        "3. End with a 'Sources:' line using relevant chunk IDs.\n"
        f"4. Available citation IDs: {citation_list}."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _call_chat_llm(messages: list[dict[str, str]]) -> str:
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    body = {
        "model": settings.CHAT_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }

    response = httpx.post(
        settings.OPENROUTER_BASE_URL,
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
            "X-Title": settings.OPENROUTER_APP_TITLE,
        },
        json=body,
        timeout=settings.CHAT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    text = _extract_response_text(response.json())
    if not text.strip():
        raise ValueError("Chat model returned empty content.")
    return text.strip()


def _build_fallback_answer(question: str, rag_result: dict, citations: list[ChatCitation]) -> str:
    fallback = _normalize_whitespace(str(rag_result.get("final_answer") or ""))
    if not fallback:
        if citations:
            bullets = [f"- {citation.title}: {citation.snippet}" for citation in citations[:2]]
            fallback = (
                "LLM response is unavailable. Here are relevant policy points from retrieval:\n"
                + "\n".join(bullets)
            )
        else:
            fallback = (
                "LLM response is unavailable and policy retrieval returned no supporting chunks. "
                "Please retry with a more specific underwriting policy question."
            )

    if not re.search(r"(?im)^sources\s*:", fallback) and citations:
        chunk_ids = ", ".join(dict.fromkeys([citation.chunk_id for citation in citations]))
        fallback = f"{fallback}\n\nSources: {chunk_ids}"

    if "Question:" not in fallback and fallback.startswith("The answer below is a grounded fallback"):
        fallback = (
            "The answer below is a grounded fallback because the configured generation model was not available.\n\n"
            f"Question: {question}\n\n"
            f"{fallback}"
        )

    return fallback


def _ensure_sources_line(answer: str, citations: list[ChatCitation]) -> str:
    cleaned = answer.strip()
    if not citations:
        return cleaned

    if re.search(r"(?im)^sources\s*:", cleaned):
        return cleaned

    chunk_ids = ", ".join(dict.fromkeys([citation.chunk_id for citation in citations]))
    return f"{cleaned}\n\nSources: {chunk_ids}"


def _retrieve_policy_result(query: str) -> dict:
    try:
        return answer_policy_query_fast(
            query=query,
            top_k=MAX_CITATIONS,
            semantic_k=4,
            keyword_k=4,
        )
    except Exception:
        return {
            "context": "",
            "final_answer": "Policy retrieval is currently unavailable.",
            "reranked_docs": [],
        }


def build_chat_response(payload: ChatRequest) -> ChatResponse:
    session_id, prior_messages = _get_or_create_session(payload.session_id)
    rag_result = _retrieve_policy_result(payload.message)

    citations = _build_citations(rag_result)
    retrieval_context = str(rag_result.get("context") or "")
    memory_context = _format_memory_context(prior_messages)

    llm_used = False
    try:
        messages = _build_chat_messages(
            payload=payload,
            memory_context=memory_context,
            retrieval_context=retrieval_context,
            citation_ids=[item.chunk_id for item in citations],
        )
        answer = _call_chat_llm(messages)
        llm_used = True
    except Exception:
        answer = _build_fallback_answer(payload.message, rag_result, citations)

    answer = _ensure_sources_line(answer, citations)
    memory_state = _append_turn(session_id, payload.message, answer)

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        citations=citations,
        llm_used=llm_used,
        memory=memory_state,
    )
