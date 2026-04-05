from app.models.schemas import ExplanationRequest, ExplanationResponse


def build_explanation(payload: ExplanationRequest) -> ExplanationResponse:
    applicant = payload.applicant_processor_output
    default_output = payload.default_model_output
    anomaly_output = payload.anomaly_model_output
    policy_output = payload.policy_retrieval_output
    orchestrator = payload.orchestrator_output

    recommended_action = (
        orchestrator.recommended_action
        if orchestrator and orchestrator.recommended_action
        else "manual_review"
    )

    summary_parts: list[str] = []
    model_explanation: list[str] = []
    anomaly_explanation: list[str] = []
    policy_explanation: list[str] = []
    limitations: list[str] = []

    if default_output and default_output.default_probability is not None:
        band = default_output.risk_band or "unclassified"
        summary_parts.append(
            f"The predicted default probability is {default_output.default_probability:.2f} ({band} risk)."
        )
        for feat in default_output.top_features[:3]:
            model_explanation.append(
                f"{feat.feature} contributed to the risk assessment."
            )
    else:
        limitations.append("Default model evidence was not provided.")

    if anomaly_output and anomaly_output.anomaly_score is not None:
        summary_parts.append(
            f"The anomaly score is {anomaly_output.anomaly_score:.2f}."
        )
        for reason in anomaly_output.top_anomaly_reasons[:3]:
            if reason.reason:
                anomaly_explanation.append(f"{reason.feature}: {reason.reason}")
            else:
                anomaly_explanation.append(f"{reason.feature} appears atypical.")
    else:
        limitations.append("Anomaly model evidence was not provided.")

    if policy_output and policy_output.retrieved_rules:
        for rule in policy_output.retrieved_rules:
            if rule.matched:
                policy_explanation.append(rule.snippet)
    else:
        limitations.append("Policy retrieval evidence was not provided.")

    if applicant.missing_fields:
        limitations.append(
            "Missing or unidentifiable fields: " + ", ".join(applicant.missing_fields)
        )

    if applicant.suspicious_fields:
        limitations.extend(
            [f"{item.field}: {item.reason}" for item in applicant.suspicious_fields]
        )

    if orchestrator and orchestrator.decision_reasons:
        summary_parts.append(
            "Decision reasons: " + "; ".join(orchestrator.decision_reasons) + "."
        )

    summary = " ".join(summary_parts) or "Insufficient evidence was provided for a detailed explanation."

    return ExplanationResponse(
        application_id=payload.application_id,
        recommended_action=recommended_action,
        summary=summary,
        model_explanation=model_explanation,
        anomaly_explanation=anomaly_explanation,
        policy_explanation=policy_explanation,
        limitations=limitations,
    )