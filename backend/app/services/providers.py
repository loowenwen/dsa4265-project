import os
import logging
from pathlib import Path

from app.models.schemas import (
    AnomalyModelOutput,
    DefaultModelOutput,
    PolicyMatch,
    PolicyRetrievalOutput,
    TopFeature,
)


logger = logging.getLogger(__name__)
# Ensure provider logs are visible even if the app doesn't configure logging.
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = True  # also send to uvicorn/root


# Default to the bundled artifact path; override with env var CREDIT_MODEL_PATH if needed.
# Use path relative to project backend root (app/…)
DEFAULT_MODEL_PATH = os.getenv("CREDIT_MODEL_PATH", "app/models/credit_risk_lgbm.joblib")


def _feature_vector_to_prediction_record(feature_vector) -> dict:
    """
    Map the app's FeatureVector into the predictor's expected schema.
    Many predictor fields are optional; fill what we have and leave others as None.
    """
    return {
        "person_age": feature_vector.person_age,
        "person_income": feature_vector.person_income,
        "person_home_ownership": feature_vector.person_home_ownership,
        # model expects years; feature_vector stores years already
        "person_emp_length": feature_vector.person_emp_length,
        "loan_intent": feature_vector.loan_intent,
        "loan_grade": feature_vector.loan_grade,
        "loan_amnt": feature_vector.loan_amnt,
        "loan_int_rate": feature_vector.loan_int_rate,
        "loan_percent_income": feature_vector.loan_percent_income,
        "cb_person_default_on_file": feature_vector.cb_person_default_on_file,
        "cb_person_cred_hist_length": feature_vector.cb_person_cred_hist_length,
    }


def get_default_model_output(feature_vector) -> DefaultModelOutput:
    model_path = Path(DEFAULT_MODEL_PATH)

    # Prefer real predictor if model artifact is available; otherwise fall back to stub.
    if model_path.exists():
        try:
            from app.services.credit_risk_predictor import predict_one_record

            record = _feature_vector_to_prediction_record(feature_vector)
            prediction = predict_one_record(str(model_path), record, top_n=5)

            top_features = [
                TopFeature(
                    feature=item.get("feature", ""),
                    value=item.get("feature_value"),
                    direction=item.get("effect", "unknown") if item.get("effect") in ("increase_risk", "decrease_risk") else "unknown",
                    importance=item.get("contribution_to_probability"),
                )
                for item in prediction.get("top_features", [])
            ]

            probability = prediction.get("default_probability")
            logger.info("[providers] default model used: prob=%s path=%s", probability, model_path)
            print(f"[providers] default model used: prob={probability} path={model_path}")

            return DefaultModelOutput(
                model_name="credit_risk_predictor",
                default_probability=probability,
                risk_band=prediction.get("risk_level"),
                confidence=None,
                in_distribution=True,
                top_features=top_features,
            )
        except Exception as exc:
            # Fall back to stub if the real predictor fails, but note it in logs for debugging.
            logger.warning("[providers] default model fallback to stub: %s", exc)
            print(f"[providers] default model fallback to stub: {exc}")

    else:
        logger.warning("[providers] model path not found: %s; using stub output", model_path)
        print(f"[providers] model path not found: {model_path}; using stub output")

    logger.info("[providers] using stub default model output")
    print("[providers] using stub default model output")
    return DefaultModelOutput(
        model_name="stub_default_model",
        default_probability=0.35,
        risk_band="medium",
        confidence=0.6,
        in_distribution=True,
        top_features=[
            TopFeature(feature="loan_percent_income", value=feature_vector.loan_percent_income, direction="increase_risk", importance=0.4),
            TopFeature(feature="loan_int_rate", value=feature_vector.loan_int_rate, direction="increase_risk", importance=0.3),
        ],
    )


def get_anomaly_model_output(feature_vector) -> AnomalyModelOutput:
    # TODO: replace stub with real anomaly detector
    score = 0.2 if feature_vector.loan_percent_income < 0.5 else 0.55
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
    if feature_vector.loan_percent_income > 0.6:
        rules.append(
            PolicyMatch(
                rule_id="policy_dti_60",
                title="Loan percent income exceeds 60%",
                snippet="Applicants with loan percent income above 60% require manual review.",
                severity="review",
            )
        )
    return PolicyRetrievalOutput(retrieved_rules=rules)
