from app.models.schemas import (
    ExplanationKeyMetrics,
    ExplanationRequest,
    ExplanationResponse,
)


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


def build_explanation(payload: ExplanationRequest) -> ExplanationResponse:
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
