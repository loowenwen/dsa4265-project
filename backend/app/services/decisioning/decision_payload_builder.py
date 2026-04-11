from __future__ import annotations

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


def build_consolidated_decision_payload(
    raw_input: dict,
    default_model_output: DefaultModelOutput,
    anomaly_model_output: AnomalyModelOutput,
    ai_decision: AIDecision,
    decisions: dict,
) -> ConsolidatedDecisionPayload:
    default_risk_decision = decisions["default_risk_decision"]
    anomaly_decision = decisions["anomaly_decision"]
    ai_decision_label = decisions["ai_decision_label"]
    overall_decision = decisions["overall_decision"]
    decision_note = decisions["decision_note"]

    return ConsolidatedDecisionPayload(
        overall_decision=OverallDecisionPayload(
            decision=overall_decision,
            decision_note=decision_note,
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
