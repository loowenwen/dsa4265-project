from app.models.schemas import (
    AnomalyModelOutput,
    DefaultModelOutput,
    PolicyMatch,
    PolicyRetrievalOutput,
    TopFeature,
)


def get_default_model_output(feature_vector) -> DefaultModelOutput:
    # TODO: replace stub with real model inference
    return DefaultModelOutput(
        model_name="stub_default_model",
        default_probability=0.35,
        risk_band="medium",
        confidence=0.6,
        in_distribution=True,
        top_features=[
            TopFeature(feature="debt_to_income_ratio", value=feature_vector.debt_to_income_ratio, direction="increase_risk", importance=0.4),
            TopFeature(feature="recent_delinquencies", value=feature_vector.recent_delinquencies, direction="increase_risk", importance=0.3),
        ],
    )


def get_anomaly_model_output(feature_vector) -> AnomalyModelOutput:
    # TODO: replace stub with real anomaly detector
    score = 0.2 if feature_vector.debt_to_income_ratio < 50 else 0.55
    return AnomalyModelOutput(
        model_name="stub_anomaly_model",
        anomaly_score=score,
        anomaly_band="elevated" if score >= 0.5 else "normal",
        out_of_distribution=False,
        top_anomaly_reasons=[],
    )


def get_policy_retrieval_output(feature_vector) -> PolicyRetrievalOutput:
    # TODO: replace stub with real policy retrieval
    rules = []
    if feature_vector.debt_to_income_ratio > 60:
        rules.append(
            PolicyMatch(
                rule_id="policy_dti_60",
                title="DTI exceeds 60%",
                snippet="Applicants with DTI above 60% require manual review.",
                severity="review",
            )
        )
    return PolicyRetrievalOutput(retrieved_rules=rules)
