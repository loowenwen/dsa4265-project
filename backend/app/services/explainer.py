import json
import re

import httpx

from app.core import settings
from app.models.schemas import ExplanationKeyMetrics, ExplanationRequest, ExplanationResponse


ACTION_MAP = {
    "APPROVE": "accept",
    "REJECT": "reject",
    "MANUAL_REVIEW": "manual review",
}


def _normalize_action(raw_action: str | None) -> str:
    return ACTION_MAP.get(raw_action or "", "manual review")


def _format_probability(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value:.2f}"


def _build_base_explanation(payload: ExplanationRequest) -> ExplanationResponse:
    applicant = payload.applicant_processor_output
    default_output = payload.default_model_output
    anomaly_output = payload.anomaly_model_output
    policy_output = payload.policy_retrieval_output
    orchestrator = payload.orchestrator_output

    recommended_action = _normalize_action(
        orchestrator.recommendation if orchestrator else None
    )

    reasons: list[str] = []
    policy_references: list[str] = []
    limitations: list[str] = []

    default_probability = None
    anomaly_score = None

    if orchestrator and orchestrator.evidence:
        default_probability = orchestrator.evidence.default_probability
        anomaly_score = orchestrator.evidence.anomaly_score

    if default_probability is None and default_output:
        default_probability = default_output.default_probability

    if anomaly_score is None and anomaly_output:
        anomaly_score = anomaly_output.anomaly_score

    if default_probability is not None:
        risk_band = default_output.risk_band if default_output else None
        band_text = f", which falls in the {risk_band} risk band" if risk_band else ""
        reasons.append(
            f"The predicted probability of default is {_format_probability(default_probability)}{band_text}."
        )
    else:
        limitations.append("Default model evidence was not provided.")

    if anomaly_score is not None:
        anomaly_band = anomaly_output.anomaly_band if anomaly_output else None
        band_text = (
            f" and is classified as {anomaly_band}" if anomaly_band else ""
        )
        anomaly_sentence = (
            f"The anomaly score is {_format_probability(anomaly_score)}{band_text}."
        )
        if anomaly_output and anomaly_output.out_of_distribution:
            anomaly_sentence += " The profile is flagged as out-of-distribution."
        reasons.append(anomaly_sentence)
    else:
        limitations.append("Anomaly model evidence was not provided.")

    if policy_output and policy_output.retrieved_rules:
        for rule in policy_output.retrieved_rules:
            if rule.matched:
                label = rule.title or rule.rule_id or "Policy rule"
                policy_references.append(label)
    elif orchestrator and orchestrator.evidence and orchestrator.evidence.violated_policy_titles:
        policy_references.extend(orchestrator.evidence.violated_policy_titles)
    else:
        limitations.append("Policy retrieval evidence was not provided.")

    if policy_references:
        reasons.append(
            "Relevant policy checks were triggered: "
            + ", ".join(policy_references)
            + "."
        )

    if applicant.missing_fields:
        limitations.append(
            "Missing or unidentifiable fields: " + ", ".join(applicant.missing_fields)
        )

    if applicant.suspicious_fields:
        limitations.extend(
            [f"{item.field}: {item.reason}" for item in applicant.suspicious_fields]
        )

    if default_output and default_output.top_features:
        top_features = []
        for feat in default_output.top_features[:2]:
            if feat.feature:
                top_features.append(feat.feature.replace("_", " "))
        if top_features:
            reasons.append(
                "The credit risk estimate is driven mainly by "
                + " and ".join(top_features)
                + "."
            )

    if anomaly_output and anomaly_output.top_anomaly_reasons:
        anomaly_reasons = []
        for item in anomaly_output.top_anomaly_reasons[:2]:
            if item.reason:
                anomaly_reasons.append(item.reason)
            elif item.feature:
                anomaly_reasons.append(f"an unusual pattern in {item.feature.replace('_', ' ')}")
        if anomaly_reasons:
            reasons.append(
                "The anomaly review also notes "
                + " and ".join(anomaly_reasons)
                + "."
            )

    if orchestrator and orchestrator.summary:
        reasons.append(orchestrator.summary)

    if not reasons:
        reasons.append(
            "There is not enough consolidated evidence to explain the decision, so manual review is recommended."
        )

    reasons_text = " ".join(reasons)

    return ExplanationResponse(
        application_id=payload.application_id,
        recommended_action=recommended_action,
        key_metrics=ExplanationKeyMetrics(
            probability_of_default=default_probability,
            anomaly_score=anomaly_score,
            risk_band=default_output.risk_band if default_output else None,
            anomaly_band=anomaly_output.anomaly_band if anomaly_output else None,
        ),
        reasons=reasons_text,
        reason_codes=orchestrator.reason_codes if orchestrator else [],
        policy_references=policy_references,
        decision_path=orchestrator.decision_path if orchestrator else None,
        limitations=limitations,
    )


def _build_grounded_llm_prompt(
    payload: ExplanationRequest,
    fallback: ExplanationResponse,
) -> dict:
    default_output = payload.default_model_output
    anomaly_output = payload.anomaly_model_output
    policy_output = payload.policy_retrieval_output
    orchestrator = payload.orchestrator_output

    return {
        "recommendation": fallback.recommended_action,
        "decision_path": orchestrator.decision_path if orchestrator else None,
        "orchestrator_summary": orchestrator.summary if orchestrator else None,
        "reason_codes": fallback.reason_codes,
        "metrics": {
            "probability_of_default": fallback.key_metrics.probability_of_default,
            "anomaly_score": fallback.key_metrics.anomaly_score,
            "risk_band": fallback.key_metrics.risk_band,
            "anomaly_band": fallback.key_metrics.anomaly_band,
        },
        "risk_evidence": [
            {
                "feature": feature.feature,
                "direction": feature.direction,
                "importance": feature.importance,
            }
            for feature in (default_output.top_features if default_output else [])[:3]
        ],
        "anomaly_evidence": [
            {
                "feature": item.feature,
                "reason": item.reason,
                "severity": item.severity,
            }
            for item in (anomaly_output.top_anomaly_reasons if anomaly_output else [])[:3]
        ],
        "policy_references": fallback.policy_references
        or [
            rule.title or rule.rule_id or "Policy rule"
            for rule in (policy_output.retrieved_rules if policy_output else [])
            if rule.matched
        ],
        "limitations": fallback.limitations,
    }


def _extract_response_text(response_json: dict) -> str:
    if response_json.get("output_text"):
        return response_json["output_text"]

    output = response_json.get("output", [])
    for item in output:
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]

    raise ValueError("No output text returned by explanation model.")


def _allowed_reason_codes(payload: ExplanationRequest) -> set[str]:
    orchestrator = payload.orchestrator_output
    return set(orchestrator.reason_codes if orchestrator else [])


def _allowed_policy_titles(payload: ExplanationRequest) -> set[str]:
    policy_output = payload.policy_retrieval_output
    titles = set()
    if policy_output:
        titles.update(
            rule.title or rule.rule_id or "Policy rule"
            for rule in policy_output.retrieved_rules
            if rule.matched
        )
    orchestrator = payload.orchestrator_output
    if orchestrator and orchestrator.evidence and orchestrator.evidence.violated_policy_titles:
        titles.update(orchestrator.evidence.violated_policy_titles)
    return titles


def _allowed_metric_strings(fallback: ExplanationResponse) -> set[str]:
    allowed = set()
    if fallback.key_metrics.probability_of_default is not None:
        allowed.add(f"{fallback.key_metrics.probability_of_default:.2f}")
        allowed.add(str(fallback.key_metrics.probability_of_default))
    if fallback.key_metrics.anomaly_score is not None:
        allowed.add(f"{fallback.key_metrics.anomaly_score:.2f}")
        allowed.add(str(fallback.key_metrics.anomaly_score))
    return allowed


def _validate_llm_output(
    parsed: dict,
    payload: ExplanationRequest,
    fallback: ExplanationResponse,
) -> tuple[str, list[str], list[str]]:
    reasons = parsed.get("reasons")
    cited_reason_codes = parsed.get("used_reason_codes", [])
    cited_policy_titles = parsed.get("used_policy_titles", [])

    if not isinstance(reasons, str) or not reasons.strip():
        raise ValueError("LLM explanation is empty.")

    if not isinstance(cited_reason_codes, list) or not all(
        isinstance(item, str) for item in cited_reason_codes
    ):
        raise ValueError("Invalid reason code citations from LLM.")

    if not isinstance(cited_policy_titles, list) or not all(
        isinstance(item, str) for item in cited_policy_titles
    ):
        raise ValueError("Invalid policy citations from LLM.")

    allowed_reason_codes = _allowed_reason_codes(payload)
    if any(code not in allowed_reason_codes for code in cited_reason_codes):
        raise ValueError("LLM cited unsupported reason codes.")

    allowed_policy_titles = _allowed_policy_titles(payload)
    if any(title not in allowed_policy_titles for title in cited_policy_titles):
        raise ValueError("LLM cited unsupported policy titles.")

    allowed_metric_strings = _allowed_metric_strings(fallback)
    numeric_tokens = re.findall(r"\b\d+\.\d+\b", reasons)
    if any(token not in allowed_metric_strings for token in numeric_tokens):
        raise ValueError("LLM introduced unsupported numeric claims.")

    return reasons.strip(), cited_reason_codes, cited_policy_titles


def _generate_llm_reason_text(
    payload: ExplanationRequest,
    fallback: ExplanationResponse,
) -> tuple[str, list[str], list[str]]:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")

    prompt_payload = _build_grounded_llm_prompt(payload, fallback)
    body = {
        "model": settings.EXPLANATION_MODEL,
        "instructions": (
            "You are a credit decision explanation assistant. "
            "The recommendation is already decided and cannot be changed. "
            "Use only the evidence provided. "
            "Do not add thresholds, policies, facts, or reasons that are not present. "
            "Do not mention any numeric values except the provided probability of default and anomaly score. "
            "Write one concise paragraph for the explanation."
        ),
        "input": json.dumps(prompt_payload),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "grounded_credit_explanation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "reasons": {"type": "string"},
                        "used_reason_codes": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "used_policy_titles": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["reasons", "used_reason_codes", "used_policy_titles"],
                    "additionalProperties": False,
                },
            }
        },
    }

    response = httpx.post(
        f"{settings.OPENAI_BASE_URL}/responses",
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=settings.EXPLANATION_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    parsed = json.loads(_extract_response_text(response.json()))
    return _validate_llm_output(parsed, payload, fallback)


def build_explanation(payload: ExplanationRequest) -> ExplanationResponse:
    fallback = _build_base_explanation(payload)

    try:
        reasons, cited_reason_codes, cited_policy_titles = _generate_llm_reason_text(
            payload, fallback
        )
        fallback.reasons = reasons
        if cited_reason_codes:
            fallback.reason_codes = cited_reason_codes
        if cited_policy_titles:
            fallback.policy_references = cited_policy_titles
        return fallback
    except Exception as exc:
        fallback.limitations.append(
            f"LLM explanation unavailable; used deterministic fallback ({str(exc)})."
        )
        return fallback
