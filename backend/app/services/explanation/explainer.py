import json
import re

import httpx

from app.core import settings
from app.models.schemas import (
    ConsolidatedDecisionPayload,
    ExplanationEvidenceItem,
    ExplanationKeyMetrics,
    ExplanationRequest,
    ExplanationResponse,
)


ALLOWED_SOURCES = {"default_risk", "anomaly_detection", "ai_decision"}


def _unavailable_response(payload: ExplanationRequest, reason: str) -> ExplanationResponse:
    decision_payload = payload.decision_payload
    return ExplanationResponse(
        application_id=payload.application_id,
        overall_decision=decision_payload.overall_decision.decision,
        key_metrics=ExplanationKeyMetrics(
            probability_of_default=decision_payload.default_risk.default_probability,
            anomaly_score=decision_payload.anomaly_detection.anomaly_score,
            risk_band=decision_payload.default_risk.risk_band,
            anomaly_band=decision_payload.anomaly_detection.anomaly_band,
        ),
        summary=(
            "Explanation unavailable. The system could not generate a grounded AI explanation "
            "for this case using the available evidence."
        ),
        supporting_evidence=[],
        cautionary_evidence=[],
        limitations=[reason],
    )


def _extract_response_text(response_json: dict) -> str:
    choices = response_json.get("choices", [])
    for choice in choices:
        message = choice.get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

    raise ValueError("No output text returned by OpenRouter explanation model.")


def _allowed_numeric_tokens(decision_payload: ConsolidatedDecisionPayload) -> set[str]:
    raw = json.dumps(decision_payload.model_dump())
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", raw))


def _validate_evidence_items(items: list[dict], allowed_numeric_tokens: set[str]) -> list[ExplanationEvidenceItem]:
    validated: list[ExplanationEvidenceItem] = []

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Evidence item must be an object.")
        text = item.get("text")
        sources = item.get("sources", [])
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Evidence text is required.")
        if not isinstance(sources, list) or not all(isinstance(src, str) for src in sources):
            raise ValueError("Evidence sources must be a string list.")
        if any(src not in ALLOWED_SOURCES for src in sources):
            raise ValueError("Evidence cited unsupported source.")
        numeric_tokens = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        if any(token not in allowed_numeric_tokens for token in numeric_tokens):
            raise ValueError("Evidence introduced unsupported numeric claims.")
        validated.append(ExplanationEvidenceItem(text=text.strip(), sources=sources))

    return validated


def _validate_llm_output(parsed: dict, decision_payload: ConsolidatedDecisionPayload) -> tuple[str, list[ExplanationEvidenceItem], list[ExplanationEvidenceItem]]:
    summary = parsed.get("summary")
    supporting = parsed.get("supporting_evidence", [])
    cautionary = parsed.get("cautionary_evidence", [])

    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("LLM summary is empty.")

    allowed_numeric_tokens = _allowed_numeric_tokens(decision_payload)
    summary_numeric = re.findall(r"\b\d+(?:\.\d+)?\b", summary)
    if any(token not in allowed_numeric_tokens for token in summary_numeric):
        raise ValueError("Summary introduced unsupported numeric claims.")

    supporting_items = _validate_evidence_items(supporting, allowed_numeric_tokens)
    cautionary_items = _validate_evidence_items(cautionary, allowed_numeric_tokens)
    return summary.strip(), supporting_items, cautionary_items


def _generate_llm_explanation(
    payload: ExplanationRequest,
) -> tuple[str, list[ExplanationEvidenceItem], list[ExplanationEvidenceItem]]:
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    decision_payload = payload.decision_payload
    system_prompt = (
        "You are a credit-risk explanation assistant for a loan underwriting system. "
        "Your job is to explain the final recommendation to a client in clear, professional language. "
        "Important rules: "
        "The decision has already been made by the decision maker. Do not change it. "
        "Use only the evidence provided. "
        "Do not invent policies, thresholds, facts, or reasons. "
        "Do not mention any number unless it appears in the evidence. "
        "If evidence is insufficient, say the explanation is unavailable. "
        "Keep the tone professional, concise, and easy for a non-technical client to understand. "
        "Group the explanation into one summary, supporting evidence, and cautionary evidence. "
        "Each evidence point must cite one or more of these source labels only: "
        "default_risk, anomaly_detection, ai_decision. "
        "Each evidence item should be a complete, client-facing explanation of why that signal supports or cautions the decision, "
        "not just a short feature restatement. "
        "Prefer 1 to 2 full sentences per evidence item. "
        "Explain the implication of the signal in plain language. "
        "Whenever a metric or feature is relevant, include the exact numeric value or categorical value from the evidence payload. "
        "If you mention default risk, include the default probability. "
        "If you mention anomaly, include the anomaly score. "
        "If you mention a top feature, include its actual value where available. "
        "Do not use vague phrases like moderate risk, elevated concern, or normal range unless you tie them directly to the provided values. "
        "Avoid brackets, shorthand labels, or parenthetical source mentions inside the text itself because sources are provided separately. "
        "Return valid JSON only."
    )
    body = {
        "model": settings.EXPLANATION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": json.dumps(decision_payload.model_dump()),
            },
        ],
        "temperature": 0.1,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "grounded_credit_explanation_v2",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "supporting_evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "sources": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "enum": ["default_risk", "anomaly_detection", "ai_decision"],
                                        },
                                    },
                                },
                                "required": ["text", "sources"],
                                "additionalProperties": False,
                            },
                        },
                        "cautionary_evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "sources": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "enum": ["default_risk", "anomaly_detection", "ai_decision"],
                                        },
                                    },
                                },
                                "required": ["text", "sources"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["summary", "supporting_evidence", "cautionary_evidence"],
                    "additionalProperties": False,
                },
            },
        },
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
        timeout=settings.EXPLANATION_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    parsed = json.loads(_extract_response_text(response.json()))
    return _validate_llm_output(parsed, decision_payload)


def build_explanation(payload: ExplanationRequest) -> ExplanationResponse:
    try:
        summary, supporting_evidence, cautionary_evidence = _generate_llm_explanation(
            payload
        )
        decision_payload = payload.decision_payload
        return ExplanationResponse(
            application_id=payload.application_id,
            overall_decision=decision_payload.overall_decision.decision,
            key_metrics=ExplanationKeyMetrics(
                probability_of_default=decision_payload.default_risk.default_probability,
                anomaly_score=decision_payload.anomaly_detection.anomaly_score,
                risk_band=decision_payload.default_risk.risk_band,
                anomaly_band=decision_payload.anomaly_detection.anomaly_band,
            ),
            summary=summary,
            supporting_evidence=supporting_evidence,
            cautionary_evidence=cautionary_evidence,
            limitations=[],
        )
    except Exception as exc:
        return _unavailable_response(payload, f"LLM explanation unavailable ({str(exc)}).")
