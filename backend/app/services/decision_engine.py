"""
Dual decision engine: deterministic rule path + AI (LLM-style) second opinion.
AI path is stubbed heuristics to stay runnable; replace with real LLM call later.
"""

from __future__ import annotations

from typing import Literal

import os
import json
import httpx

from app.core import decision_config as cfg
from app.models.schemas import (
    AIDecision,
    DecisionAlignment,
    PolicyRetrievalOutput,
    RuleDecision,
)


Decision = Literal["APPROVE", "REJECT", "MANUAL_REVIEW"]


def _rule_based_decision(
    default_probability: float | None,
    anomaly_score: float | None,
    missing_fields: list[str],
    suspicious_fields: list[str],
) -> RuleDecision:
    reasons: list[str] = []
    triggered: list[str] = []

    # Missing info -> manual review, but ignore demographic_information
    filtered_missing = [f for f in missing_fields if f != "demographic_information"]
    if filtered_missing:
        reasons.append("Missing required information")
        return RuleDecision(
            decision="MANUAL_REVIEW",
            reasons=reasons,
            triggered_rules=["INCOMPLETE_DATA"],
            missing_info=filtered_missing,
            confidence=0.4,
        )

    # High risk reject
    if default_probability is not None and default_probability >= cfg.REJECT_THRESHOLD:
        reasons.append("Default risk above reject threshold")
        triggered.append("HIGH_DEFAULT_RISK")
        return RuleDecision(
            decision="REJECT",
            reasons=reasons,
            triggered_rules=triggered,
            missing_info=[],
            confidence=0.7,
        )

    # Anomaly check
    if anomaly_score is not None and anomaly_score >= cfg.ANOMALY_REVIEW_THRESHOLD:
        reasons.append("Elevated anomaly score")
        triggered.append("ELEVATED_ANOMALY")
        return RuleDecision(
            decision="MANUAL_REVIEW",
            reasons=reasons,
            triggered_rules=triggered,
            missing_info=[],
            confidence=0.5,
        )

    # Suspicious fields
    if suspicious_fields:
        reasons.append("Suspicious input values present")
        triggered.append("SUSPICIOUS_INPUT")
        return RuleDecision(
            decision="MANUAL_REVIEW",
            reasons=reasons,
            triggered_rules=triggered,
            missing_info=[],
            confidence=0.5,
        )

    # Low risk approve
    if default_probability is not None and default_probability < cfg.APPROVE_THRESHOLD:
        reasons.append("Low default risk below approve threshold")
        triggered.append("LOW_RISK_CLEAR_POLICY")
        return RuleDecision(
            decision="APPROVE",
            reasons=reasons,
            triggered_rules=triggered,
            missing_info=[],
            confidence=0.75,
        )

    # Fallback manual review
    reasons.append("Insufficient certainty; manual review")
    return RuleDecision(
        decision="MANUAL_REVIEW",
        reasons=reasons,
        triggered_rules=["FALLBACK_REVIEW"],
        missing_info=[],
        confidence=0.5,
    )


def _fallback_ai_decision(
    default_probability: float | None,
    anomaly_score: float | None,
    missing_fields: list[str],
    policy_snippets: list[str],
) -> AIDecision:
    """Deterministic heuristic fallback when LLM is unavailable."""
    reasons: list[str] = []
    policy_considerations: list[str] = policy_snippets[:3] if policy_snippets else []

    if missing_fields:
        reasons.append("Data incomplete; request manual review")
        return AIDecision(
            decision="MANUAL_REVIEW",
            confidence=0.4,
            reasons=reasons,
            missing_info=missing_fields,
            policy_considerations=policy_considerations,
        )

    if default_probability is not None and default_probability >= cfg.REJECT_THRESHOLD:
        reasons.append("Elevated default probability")
        return AIDecision(
            decision="REJECT",
            confidence=0.65,
            reasons=reasons,
            missing_info=[],
            policy_considerations=policy_considerations,
        )

    if anomaly_score is not None and anomaly_score >= cfg.ANOMALY_REVIEW_THRESHOLD:
        reasons.append("Anomaly flags require human review")
        return AIDecision(
            decision="MANUAL_REVIEW",
            confidence=0.5,
            reasons=reasons,
            missing_info=[],
            policy_considerations=policy_considerations,
        )

    if default_probability is not None and default_probability < cfg.APPROVE_THRESHOLD:
        reasons.append("Risk acceptable; proceed to approve")
        return AIDecision(
            decision="APPROVE",
            confidence=0.7,
            reasons=reasons,
            missing_info=[],
            policy_considerations=policy_considerations,
        )

    reasons.append("Mixed signals; manual review recommended")
    return AIDecision(
        decision="MANUAL_REVIEW",
        confidence=0.5,
        reasons=reasons,
        missing_info=[],
        policy_considerations=policy_considerations,
    )


def _call_openrouter_llm(prompt: str) -> dict | None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    # Default to a lightweight, widely available model
    model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")
    if not api_key:
        return None
    try:
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _parse_ai_completion(raw: dict) -> tuple[Decision, float | None, list[str]]:
    # Expect a concise JSON in the first message content if present.
    try:
        content = raw["choices"][0]["message"]["content"]
        data = json.loads(content)
        decision = data.get("decision")
        reasons = data.get("reasons", [])
        confidence = data.get("confidence")
        if decision in ("APPROVE", "REJECT", "MANUAL_REVIEW"):
            return decision, confidence, reasons
    except Exception:
        pass
    return "MANUAL_REVIEW", 0.5, ["LLM response invalid; default to manual review"]


def _ai_underwriting_decision(
    applicant: dict,
    default_probability: float | None,
    anomaly_score: float | None,
    missing_fields: list[str],
    policy_snippets: list[str],
) -> AIDecision:
    """
    AI path: tries OpenRouter LLM when configured; otherwise falls back to deterministic heuristic.
    """
    policy_considerations: list[str] = policy_snippets[:3] if policy_snippets else []

    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        prompt = (
            "You are an internal underwriting assistant. Decide APPROVE, REJECT, or MANUAL_REVIEW. "
            "If information is incomplete or conflicting, choose MANUAL_REVIEW. "
            "Use only provided facts; do not invent policy. "
            "Return JSON: {\"decision\": \"APPROVE|REJECT|MANUAL_REVIEW\", "
            "\"confidence\": float, \"reasons\": [\"...\"]}.\n\n"
            f"Applicant: {json.dumps(applicant)}\n"
            f"Default probability: {default_probability}\n"
            f"Anomaly score: {anomaly_score}\n"
            f"Missing fields: {missing_fields}\n"
            f"Policy snippets: {policy_considerations}\n"
        )
        raw = _call_openrouter_llm(prompt)
        if raw:
            decision, conf, reasons = _parse_ai_completion(raw)
            return AIDecision(
                decision=decision,
                confidence=conf,
                reasons=reasons,
                missing_info=missing_fields,
                policy_considerations=policy_considerations,
            )

    # Fallback if no API key or LLM fails
    return _fallback_ai_decision(default_probability, anomaly_score, missing_fields, policy_snippets)


def _alignment(rule_decision: RuleDecision, ai_decision: AIDecision) -> DecisionAlignment:
    status: Literal["AGREE", "DISAGREE"] = (
        "AGREE" if rule_decision.decision == ai_decision.decision else "DISAGREE"
    )
    note = None
    if status == "DISAGREE":
        note = f"Rule decision={rule_decision.decision}, AI decision={ai_decision.decision}"
    return DecisionAlignment(status=status, note=note)


def run_dual_engine(
    applicant: dict,
    default_probability: float | None,
    anomaly_score: float | None,
    missing_fields: list[str],
    suspicious_fields: list[str],
    policy_output: PolicyRetrievalOutput | None,
) -> tuple[RuleDecision, AIDecision, DecisionAlignment]:
    filtered_missing = [f for f in missing_fields if f != "demographic_information"]

    rule = _rule_based_decision(default_probability, anomaly_score, filtered_missing, suspicious_fields)

    policy_snippets: list[str] = []
    if policy_output and policy_output.retrieved_rules:
        policy_snippets = [r.snippet for r in policy_output.retrieved_rules if r.snippet]

    ai = _ai_underwriting_decision(
        applicant=applicant,
        default_probability=default_probability,
        anomaly_score=anomaly_score,
        missing_fields=filtered_missing,
        policy_snippets=policy_snippets,
    )
    align = _alignment(rule, ai)
    return rule, ai, align
