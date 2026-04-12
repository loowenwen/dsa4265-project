"""
Dual decision engine: deterministic rule path + AI (LLM-style) second opinion.
AI path is stubbed heuristics to stay runnable; replace with real LLM call later.
"""

from __future__ import annotations

from typing import Literal
import logging

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

logger = logging.getLogger(__name__)


def _map_upper_decision(decision: str | None) -> str:
    mapping = {
        "APPROVE": "accept",
        "REJECT": "reject",
        "MANUAL_REVIEW": "manual_review",
    }
    return mapping.get(decision or "", "manual_review")


def _default_risk_decision(default_probability: float | None) -> str:
    if default_probability is None:
        return "manual_review"
    if default_probability >= cfg.REJECT_THRESHOLD:
        return "reject"
    if default_probability < cfg.APPROVE_THRESHOLD:
        return "accept"
    return "manual_review"


def _anomaly_decision(anomaly_score: float | None) -> str:
    if anomaly_score is None:
        return "manual_review"
    if anomaly_score >= cfg.ANOMALY_REVIEW_THRESHOLD:
        return "manual_review"
    return "accept"


def _combine_two_votes(rule_vote: str, ai_vote: str) -> str:
    # Manual review always wins when either voter is uncertain/escalating.
    if "manual_review" in (rule_vote, ai_vote):
        return "manual_review"
    if rule_vote == ai_vote:
        return rule_vote
    if {rule_vote, ai_vote} == {"accept", "reject"}:
        return "manual_review"
    return "manual_review"


def _decision_note(rule_vote: str, ai_vote: str, overall_decision: str) -> str:
    pretty_rule = rule_vote.replace("_", " ")
    pretty_ai = ai_vote.replace("_", " ")
    pretty_final = overall_decision.replace("_", " ")

    if rule_vote == ai_vote:
        return (
            f"Rule vote is {pretty_rule} and AI vote is {pretty_ai}; "
            f"the final decision is {pretty_final} because both votes agree."
        )

    if "manual_review" in (rule_vote, ai_vote):
        return (
            f"Rule vote is {pretty_rule} and AI vote is {pretty_ai}; "
            f"the final decision is {pretty_final} because a manual-review vote overrides direct "
            "approve/reject outcomes."
        )

    return (
        f"Rule vote is {pretty_rule} and AI vote is {pretty_ai}; "
        f"the final decision is {pretty_final} because approve/reject conflict routes to manual review."
    )


def _rule_based_decision(
    default_probability: float | None,
    anomaly_score: float | None,
    missing_fields: list[str],
    suspicious_fields: list[str],
) -> RuleDecision:
    reasons: list[str] = []
    triggered: list[str] = []

    # Missing info excludes demographic_information for rule checks.
    filtered_missing = [f for f in missing_fields if f != "demographic_information"]

    # 1) Hard reject first on default probability.
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

    # 2) Elevated anomaly routes to manual review.
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

    # 3) Suspicious fields route to manual review.
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

    # 4) Missing required fields route to manual review.
    if filtered_missing:
        reasons.append("Missing required information")
        triggered.append("INCOMPLETE_DATA")
        return RuleDecision(
            decision="MANUAL_REVIEW",
            reasons=reasons,
            triggered_rules=triggered,
            missing_info=filtered_missing,
            confidence=0.4,
        )

    # 5) Low-risk approve only when anomaly score is explicitly below threshold.
    if (
        default_probability is not None
        and default_probability < cfg.APPROVE_THRESHOLD
        and anomaly_score is not None
        and anomaly_score < cfg.ANOMALY_REVIEW_THRESHOLD
    ):
        reasons.append("Low default risk below approve threshold")
        triggered.append("LOW_RISK_CLEAR_POLICY")
        return RuleDecision(
            decision="APPROVE",
            reasons=reasons,
            triggered_rules=triggered,
            missing_info=[],
            confidence=0.75,
        )

    # 6) Uncertain band fallback.
    reasons.append("Insufficient certainty; manual review")
    return RuleDecision(
        decision="MANUAL_REVIEW",
        reasons=reasons,
        triggered_rules=["FALLBACK_REVIEW"],
        missing_info=[],
        confidence=0.5,
    )


def _fallback_ai_decision(applicant: dict) -> AIDecision:
    """Deterministic heuristic fallback when LLM is unavailable."""
    reasons: list[str] = []

    loan_percent_income = applicant.get("loan_percent_income")
    loan_grade = str(applicant.get("loan_grade", "")).upper()

    if isinstance(loan_percent_income, (int, float)) and loan_percent_income >= 0.6:
        reasons.append("High requested debt-to-income share based on applicant data")
        return AIDecision(
            decision="REJECT",
            confidence=0.6,
            reasons=reasons,
            missing_info=[],
            policy_considerations=[],
        )

    if loan_grade in {"E", "F", "G"}:
        reasons.append("Lower credit grade; recommend manual review")
        return AIDecision(
            decision="MANUAL_REVIEW",
            confidence=0.55,
            reasons=reasons,
            missing_info=[],
            policy_considerations=[],
        )

    if isinstance(loan_percent_income, (int, float)) and loan_percent_income < 0.2:
        reasons.append("Income share requested is modest")
        return AIDecision(
            decision="APPROVE",
            confidence=0.65,
            reasons=reasons,
            missing_info=[],
            policy_considerations=[],
        )

    reasons.append("Applicant profile warrants manual review")
    return AIDecision(
        decision="MANUAL_REVIEW",
        confidence=0.5,
        reasons=reasons,
        missing_info=[],
        policy_considerations=[],
    )


def _call_openrouter_llm(prompt: str) -> dict | None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    # Default to a lightweight, widely available model
    model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
    if not api_key:
        logger.info("[ai_decision] OPENROUTER_API_KEY not set; skipping LLM call")
        return None
    try:
        resp = httpx.post(
            base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
                "X-Title": os.getenv("OPENROUTER_APP_TITLE", "credit-risk-dual-engine"),
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=20,
        )
        resp.raise_for_status()
        logger.info("[ai_decision] openrouter call success model=%s", model)
        return resp.json()
    except Exception as exc:
        logger.warning("[ai_decision] openrouter call failed: %s", exc)
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
) -> AIDecision:
    """
    AI path: tries OpenRouter LLM when configured; otherwise falls back to deterministic heuristic.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        prompt_parts = [
            "You are an internal underwriting assistant. Decide APPROVE, REJECT, or MANUAL_REVIEW.",
            "If information is incomplete or conflicting, choose MANUAL_REVIEW.",
            "Use only the applicant information provided. Do not invent policy or rely on external risk scores.",
            'Return JSON: {"decision": "APPROVE|REJECT|MANUAL_REVIEW", "confidence": float, "reasons": ["..."]}.',
            f"Applicant: {json.dumps(applicant)}",
        ]
        prompt = "\n".join(prompt_parts)

        raw = _call_openrouter_llm(prompt)
        if raw:
            decision, conf, reasons = _parse_ai_completion(raw)
            logger.info("[ai_decision] LLM parsed decision=%s confidence=%s", decision, conf)
            return AIDecision(
                decision=decision,
                confidence=conf,
                reasons=reasons,
                missing_info=[],
                policy_considerations=[],
            )

    # Fallback if no API key or LLM fails
    return _fallback_ai_decision(applicant)


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
) -> tuple[RuleDecision, AIDecision, DecisionAlignment, dict]:
    filtered_missing = [f for f in missing_fields if f != "demographic_information"]

    rule = _rule_based_decision(default_probability, anomaly_score, filtered_missing, suspicious_fields)

    ai = _ai_underwriting_decision(
        applicant=applicant,
    )
    align = _alignment(rule, ai)

    default_risk_decision = _default_risk_decision(default_probability)
    anomaly_decision = _anomaly_decision(anomaly_score)
    rule_decision_label = _map_upper_decision(rule.decision)
    ai_decision_label = _map_upper_decision(ai.decision)
    overall_decision = _combine_two_votes(rule_decision_label, ai_decision_label)
    decision_note = _decision_note(rule_decision_label, ai_decision_label, overall_decision)

    decision_bundle = {
        "default_risk_decision": default_risk_decision,
        "anomaly_decision": anomaly_decision,
        "rule_decision_label": rule_decision_label,
        "ai_decision_label": ai_decision_label,
        "overall_decision": overall_decision,
        "decision_note": decision_note,
    }

    return rule, ai, align, decision_bundle
