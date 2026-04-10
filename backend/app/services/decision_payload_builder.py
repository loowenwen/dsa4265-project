from __future__ import annotations

from collections import Counter

from app.core import decision_config as cfg
from app.models.schemas import (
    AIDecision,
    AIDecisionPayload,
    AnomalyDetectionPayload,
    AnomalyModelOutput,
    ConsolidatedDecisionPayload,
    DecisionLabelFeature,
    DefaultModelOutput,
    DefaultRiskPayload,
    OverallDecisionPayload,
)


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


def _decision_note(
    default_risk_decision: str,
    anomaly_decision: str,
    ai_decision: str,
    overall_decision: str,
) -> str:
    labels = {
        "default_risk": default_risk_decision,
        "anomaly_detection": anomaly_decision,
        "ai_decision": ai_decision,
    }
    counts = Counter(labels.values())

    if len(counts) == 1:
        return (
            "Default risk, anomaly detection, and AI decision all suggest "
            + overall_decision.replace("_", " ")
            + "."
        )

    majority = counts.most_common(1)[0][0]
    majority_sources = [name for name, decision in labels.items() if decision == majority]
    minority_sources = [name for name, decision in labels.items() if decision != majority]

    pretty = {
        "default_risk": "Default risk",
        "anomaly_detection": "Anomaly detection",
        "ai_decision": "AI decision",
    }

    if len(majority_sources) == 2 and len(minority_sources) == 1:
        return (
            f"{pretty[majority_sources[0]]} and {pretty[majority_sources[1]]} suggest "
            f"{majority.replace('_', ' ')}, while {pretty[minority_sources[0]]} suggests "
            f"{labels[minority_sources[0]].replace('_', ' ')}."
        )

    return "The three sources provide mixed signals, so manual review is recommended."


def _overall_decision(default_risk_decision: str, anomaly_decision: str, ai_decision: str) -> str:
    counts = Counter([default_risk_decision, anomaly_decision, ai_decision])
    top_decision, top_count = counts.most_common(1)[0]
    if top_count >= 2:
        return top_decision
    return "manual_review"


def build_consolidated_decision_payload(
    raw_input: dict,
    default_model_output: DefaultModelOutput,
    anomaly_model_output: AnomalyModelOutput,
    ai_decision: AIDecision,
) -> ConsolidatedDecisionPayload:
    default_risk_decision = _default_risk_decision(default_model_output.default_probability)
    anomaly_decision = _anomaly_decision(anomaly_model_output.anomaly_score)
    ai_decision_label = _map_upper_decision(ai_decision.decision)
    overall_decision = _overall_decision(
        default_risk_decision, anomaly_decision, ai_decision_label
    )

    return ConsolidatedDecisionPayload(
        overall_decision=OverallDecisionPayload(
            decision=overall_decision,
            decision_note=_decision_note(
                default_risk_decision, anomaly_decision, ai_decision_label, overall_decision
            ),
        ),
        default_risk=DefaultRiskPayload(
            decision=default_risk_decision,
            default_probability=default_model_output.default_probability,
            risk_band=default_model_output.risk_band,
            top_features=[
                DecisionLabelFeature(
                    feature=item.feature,
                    value=item.value,
                    contribution=item.importance,
                    direction=item.direction,
                )
                for item in default_model_output.top_features[:3]
            ],
        ),
        anomaly_detection=AnomalyDetectionPayload(
            decision=anomaly_decision,
            anomaly_score=anomaly_model_output.anomaly_score,
            anomaly_band=anomaly_model_output.anomaly_band,
            top_features=[
                DecisionLabelFeature(
                    feature=item.feature,
                    value=item.value,
                    reason=item.reason,
                )
                for item in anomaly_model_output.top_anomaly_reasons[:3]
            ],
        ),
        ai_decision=AIDecisionPayload(
            decision=ai_decision_label,
            top_reasons=ai_decision.reasons[:3],
            raw_input=raw_input,
        ),
    )
