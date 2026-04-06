from typing import Literal

from app.core import decision_config as cfg
from app.models.schemas import (
    AnomalyModelOutput,
    OrchestratorInput,
    OrchestratorOutput,
    OrchestratorEvidence,
    PolicyRetrievalOutput,
)

Recommendation = Literal["APPROVE", "REJECT", "MANUAL_REVIEW"]


def _has_missing_required(data_quality) -> bool:
    missing = data_quality.missing_required_fields or []
    is_complete = data_quality.is_complete
    return bool(missing) or (is_complete is False)


def _policy_flags(policy: PolicyRetrievalOutput) -> tuple[bool, bool, list[str]]:
    hard_stop = False
    review_required = False
    titles: list[str] = []
    for rule in policy.retrieved_rules:
        if rule.title:
            titles.append(rule.title)
        if rule.severity == "hard_stop":
            hard_stop = True
        elif rule.severity == "review":
            review_required = True
    return hard_stop, review_required, titles


def decide(payload: OrchestratorInput) -> OrchestratorOutput:
    reasons: list[str] = []
    decision_path = []

    default_prob = payload.risk.default_probability
    anomaly_score = payload.anomaly.anomaly_score
    od_flag = payload.anomaly.out_of_distribution

    policy_hard_stop, policy_review_required, policy_titles = _policy_flags(payload.policy)

    # 1) Data completeness
    if _has_missing_required(payload.data_quality):
        reasons.append("INCOMPLETE_DATA")
        decision_path.append("incomplete_data")
        return OrchestratorOutput(
            recommendation="MANUAL_REVIEW",
            decision_path="manual_review -> " + " -> ".join(decision_path),
            reason_codes=reasons,
            summary="Data incomplete or unidentifiable; manual review required.",
            evidence=OrchestratorEvidence(
                default_probability=default_prob,
                anomaly_score=anomaly_score,
                violated_policy_titles=policy_titles or None,
                missing_required_fields=payload.data_quality.missing_required_fields or [],
                top_features=payload.risk.top_features or [],
                policy_review_required=policy_review_required,
                policy_hard_stop=policy_hard_stop,
            ),
        )

    # 2) Policy hard stop
    if policy_hard_stop:
        reasons.append("POLICY_HARD_STOP")
        decision_path.append("policy_hard_stop")
        return OrchestratorOutput(
            recommendation="REJECT",
            decision_path="reject -> " + " -> ".join(decision_path),
            reason_codes=reasons,
            summary="Policy hard stop triggered; reject application.",
            evidence=OrchestratorEvidence(
                default_probability=default_prob,
                anomaly_score=anomaly_score,
                violated_policy_titles=policy_titles or [],
                missing_required_fields=[],
                top_features=payload.risk.top_features or [],
                policy_review_required=policy_review_required,
                policy_hard_stop=policy_hard_stop,
            ),
        )

    # 3) High default probability
    if default_prob is not None and default_prob >= cfg.REJECT_THRESHOLD:
        reasons.append("HIGH_DEFAULT_RISK")
        decision_path.append("high_default_risk")
        return OrchestratorOutput(
            recommendation="REJECT",
            decision_path="reject -> " + " -> ".join(decision_path),
            reason_codes=reasons,
            summary="Default risk above reject threshold.",
            evidence=OrchestratorEvidence(
                default_probability=default_prob,
                anomaly_score=anomaly_score,
                violated_policy_titles=policy_titles or [],
                missing_required_fields=[],
                top_features=payload.risk.top_features or [],
                policy_review_required=policy_review_required,
                policy_hard_stop=policy_hard_stop,
            ),
        )

    # 4) Elevated anomaly / OOD / policy review
    anomaly_elevated = anomaly_score is not None and anomaly_score >= cfg.ANOMALY_REVIEW_THRESHOLD
    if od_flag:
        reasons.append("OUT_OF_DISTRIBUTION")
    if anomaly_elevated:
        reasons.append("ELEVATED_ANOMALY")
    if policy_review_required:
        reasons.append("POLICY_REVIEW_TRIGGER")
    if reasons:
        decision_path.append("review_flags")
        return OrchestratorOutput(
            recommendation="MANUAL_REVIEW",
            decision_path="manual_review -> " + " -> ".join(decision_path),
            reason_codes=reasons,
            summary="Manual review required due to policy/anomaly flags.",
            evidence=OrchestratorEvidence(
                default_probability=default_prob,
                anomaly_score=anomaly_score,
                violated_policy_titles=policy_titles or [],
                missing_required_fields=[],
                top_features=payload.risk.top_features or [],
                policy_review_required=policy_review_required,
                policy_hard_stop=policy_hard_stop,
            ),
        )

    # 5) Low risk clear policy
    if (
        default_prob is not None
        and default_prob < cfg.APPROVE_THRESHOLD
        and (anomaly_score is None or anomaly_score < cfg.ANOMALY_REVIEW_THRESHOLD)
    ):
        reasons.append("LOW_RISK_CLEAR_POLICY")
        decision_path.append("low_risk")
        return OrchestratorOutput(
            recommendation="APPROVE",
            decision_path="approve -> " + " -> ".join(decision_path),
            reason_codes=reasons,
            summary="Low default risk, no blocking policies, data complete.",
            evidence=OrchestratorEvidence(
                default_probability=default_prob,
                anomaly_score=anomaly_score,
                violated_policy_titles=policy_titles or [],
                missing_required_fields=[],
                top_features=payload.risk.top_features or [],
                policy_review_required=policy_review_required,
                policy_hard_stop=policy_hard_stop,
            ),
        )

    # Fallback manual review
    reasons.append("POLICY_REVIEW_TRIGGER" if policy_review_required else "ELEVATED_ANOMALY" if anomaly_score else "SUSPICIOUS_INPUT")
    decision_path.append("fallback_review")
    return OrchestratorOutput(
        recommendation="MANUAL_REVIEW",
        decision_path="manual_review -> " + " -> ".join(decision_path),
        reason_codes=reasons,
        summary="Insufficient confidence for auto-approval; manual review advised.",
        evidence=OrchestratorEvidence(
            default_probability=default_prob,
            anomaly_score=anomaly_score,
            violated_policy_titles=policy_titles or [],
            missing_required_fields=[],
            top_features=payload.risk.top_features or [],
            policy_review_required=policy_review_required,
            policy_hard_stop=policy_hard_stop,
        ),
    )
