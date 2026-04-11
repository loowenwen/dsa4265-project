import os
import logging
from pathlib import Path
from typing import Any

from app.models.schemas import (
    AnomalyReason,
    AnomalyModelOutput,
    DefaultModelOutput,
    PolicyMatch,
    PolicyRetrievalOutput,
    TopFeature,
)
from app.services.modeling.exceptions import ModelUnavailableError


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
ANOMALY_MODEL_DIR = os.getenv("ANOMALY_MODEL_DIR", "app/models/ae_agent")
ANOMALY_MODEL_DEVICE = os.getenv("ANOMALY_MODEL_DEVICE", "cpu")
_LAST_DEFAULT_MODEL_ERROR: str | None = None
_LAST_ANOMALY_MODEL_ERROR: str | None = None
_ANOMALY_ARTIFACT_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def _set_default_model_error(error: str | None) -> None:
    global _LAST_DEFAULT_MODEL_ERROR
    _LAST_DEFAULT_MODEL_ERROR = error


def _set_anomaly_model_error(error: str | None) -> None:
    global _LAST_ANOMALY_MODEL_ERROR
    _LAST_ANOMALY_MODEL_ERROR = error


def _resolve_model_path() -> Path:
    return Path(DEFAULT_MODEL_PATH)


def _resolve_anomaly_model_dir() -> Path:
    return Path(ANOMALY_MODEL_DIR)


def _raise_default_model_unavailable(
    message: str,
    model_path: Path,
    exc: Exception | None = None,
) -> None:
    cause = str(exc) if exc is not None else None
    full_message = f"{message}. model_path={model_path}"
    if cause:
        full_message = f"{full_message}. cause={cause}"
    _set_default_model_error(full_message)
    raise ModelUnavailableError(message=message, model_path=str(model_path), cause=cause)


def _raise_anomaly_model_unavailable(
    message: str,
    model_path: Path,
    exc: Exception | None = None,
) -> None:
    cause = str(exc) if exc is not None else None
    full_message = f"{message}. model_path={model_path}"
    if cause:
        full_message = f"{full_message}. cause={cause}"
    _set_anomaly_model_error(full_message)
    raise ModelUnavailableError(message=message, model_path=str(model_path), cause=cause)


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
    model_path = _resolve_model_path()

    if not model_path.exists():
        _raise_default_model_unavailable("Default model artifact not found", model_path)

    try:
        from app.services.modeling.credit_risk_predictor import predict_one_record
    except Exception as exc:  # pragma: no cover - depends on runtime dependency setup.
        logger.exception("[providers] failed to import default model predictor")
        _raise_default_model_unavailable(
            "Default model runtime dependencies unavailable",
            model_path,
            exc,
        )

    try:
        record = _feature_vector_to_prediction_record(feature_vector)
        prediction = predict_one_record(str(model_path), record, top_n=5)
    except Exception as exc:
        logger.exception("[providers] default model prediction failed")
        _raise_default_model_unavailable("Default model inference failed", model_path, exc)

    top_features = [
        TopFeature(
            feature=item.get("feature", ""),
            value=item.get("feature_value"),
            direction=item.get("effect", "unknown")
            if item.get("effect") in ("increase_risk", "decrease_risk")
            else "unknown",
            importance=item.get("contribution_to_probability"),
        )
        for item in prediction.get("top_features", [])
    ]

    probability = prediction.get("default_probability")
    if probability is None:
        _raise_default_model_unavailable("Default model returned null probability", model_path)

    _set_default_model_error(None)
    logger.info("[providers] default model used: prob=%s path=%s", probability, model_path)

    return DefaultModelOutput(
        model_name="credit_risk_predictor",
        default_probability=probability,
        risk_band=prediction.get("risk_level"),
        confidence=None,
        in_distribution=True,
        top_features=top_features,
    )


def _feature_vector_to_anomaly_record(feature_vector) -> dict[str, Any]:
    return {
        "person_age": feature_vector.person_age,
        "person_income": feature_vector.person_income,
        "person_home_ownership": feature_vector.person_home_ownership,
        "person_emp_length": feature_vector.person_emp_length,
        "loan_intent": feature_vector.loan_intent,
        "loan_grade": feature_vector.loan_grade,
        "loan_amnt": feature_vector.loan_amnt,
        "loan_int_rate": feature_vector.loan_int_rate,
        "loan_percent_income": feature_vector.loan_percent_income,
    }


def _load_anomaly_artifacts(artifact_dir: Path, device: str) -> dict[str, Any]:
    cache_key = (str(artifact_dir.resolve()), device)
    cached = _ANOMALY_ARTIFACT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        from app.services.modeling.anomaly_call import load_anomaly_artifacts
    except Exception as exc:
        logger.exception("[providers] failed to import anomaly model runtime")
        _raise_anomaly_model_unavailable(
            "Anomaly model runtime dependencies unavailable",
            artifact_dir,
            exc,
        )

    try:
        loaded = load_anomaly_artifacts(str(artifact_dir), device=device)
    except Exception as exc:
        logger.exception("[providers] anomaly model artifact load failed")
        _raise_anomaly_model_unavailable("Anomaly model artifact load failed", artifact_dir, exc)

    _ANOMALY_ARTIFACT_CACHE[cache_key] = loaded
    return loaded


def _score_anomaly_record(
    record: dict[str, Any],
    loaded_artifacts: dict[str, Any],
    artifact_dir: Path,
    device: str,
) -> dict[str, Any]:
    try:
        import pandas as pd
    except Exception as exc:
        _raise_anomaly_model_unavailable(
            "Anomaly model runtime dependencies unavailable",
            artifact_dir,
            exc,
        )

    try:
        from app.services.modeling.anomaly_call import score_new_applicants
    except Exception as exc:
        _raise_anomaly_model_unavailable(
            "Anomaly model runtime dependencies unavailable",
            artifact_dir,
            exc,
        )

    try:
        outputs = score_new_applicants(
            new_df=pd.DataFrame([record]),
            loaded_artifacts=loaded_artifacts,
            top_k=5,
            device=device,
        )
    except Exception as exc:
        logger.exception("[providers] anomaly model prediction failed")
        _raise_anomaly_model_unavailable("Anomaly model inference failed", artifact_dir, exc)

    if not outputs:
        _raise_anomaly_model_unavailable("Anomaly model returned empty output", artifact_dir)

    return outputs[0]


def _anomaly_severity(feature_error: float | None) -> str | None:
    if feature_error is None:
        return None
    if feature_error >= 0.25:
        return "high"
    if feature_error >= 0.1:
        return "medium"
    return "low"


def get_anomaly_model_output(feature_vector) -> AnomalyModelOutput:
    artifact_dir = _resolve_anomaly_model_dir()
    if not artifact_dir.exists():
        _raise_anomaly_model_unavailable("Anomaly model artifact directory not found", artifact_dir)

    loaded_artifacts = _load_anomaly_artifacts(artifact_dir, ANOMALY_MODEL_DEVICE)
    record = _feature_vector_to_anomaly_record(feature_vector)
    prediction = _score_anomaly_record(record, loaded_artifacts, artifact_dir, ANOMALY_MODEL_DEVICE)

    raw_score = prediction.get("anomaly_score")
    if raw_score is None:
        _raise_anomaly_model_unavailable("Anomaly model returned null score", artifact_dir)

    try:
        score = float(raw_score)
    except (TypeError, ValueError) as exc:
        _raise_anomaly_model_unavailable("Anomaly model returned non-numeric score", artifact_dir, exc)

    is_anomalous = bool(prediction.get("is_anomalous"))
    distribution_flag = str(prediction.get("distribution_flag") or "").lower()
    if distribution_flag == "out_of_distribution":
        is_anomalous = True

    reasons: list[AnomalyReason] = []
    for item in prediction.get("top_anomalous_features", []):
        feature = item.get("feature")
        if not feature:
            continue

        raw_error = item.get("feature_error")
        feature_error: float | None = None
        if isinstance(raw_error, (int, float)):
            feature_error = float(raw_error)

        reason = "Higher-than-expected reconstruction error."
        if feature_error is not None:
            reason = f"Reconstruction error={feature_error:.4f}."

        reasons.append(
            AnomalyReason(
                feature=feature,
                value=record.get(feature),
                reason=reason,
                severity=_anomaly_severity(feature_error),
            )
        )

    _set_anomaly_model_error(None)
    logger.info("[providers] anomaly model used: score=%s path=%s", score, artifact_dir)

    return AnomalyModelOutput(
        model_name="ae_agent_autoencoder",
        anomaly_score=score,
        anomaly_band="elevated" if is_anomalous else "normal",
        out_of_distribution=is_anomalous,
        top_anomaly_reasons=reasons,
    )


def get_model_readiness() -> dict[str, Any]:
    """Return model-readiness diagnostics for operational health checks."""
    model_path = _resolve_model_path()
    default_ready = False
    default_error: str | None = None

    if not model_path.exists():
        default_error = f"Model artifact not found at {model_path}"
    else:
        try:
            from app.services.modeling.credit_risk_predictor import verify_model_artifact

            verify_model_artifact(str(model_path))
            default_ready = True
            _set_default_model_error(None)
        except Exception as exc:
            default_error = str(exc)

    if default_error:
        _set_default_model_error(default_error)

    anomaly_path = _resolve_anomaly_model_dir()
    anomaly_ready = False
    anomaly_error: str | None = None

    if not anomaly_path.exists():
        anomaly_error = f"Model artifact directory not found at {anomaly_path}"
    else:
        try:
            _load_anomaly_artifacts(anomaly_path, ANOMALY_MODEL_DEVICE)
            anomaly_ready = True
            _set_anomaly_model_error(None)
        except ModelUnavailableError as exc:
            anomaly_error = str(exc)
            if exc.cause:
                anomaly_error = f"{anomaly_error}. cause={exc.cause}"
        except Exception as exc:
            anomaly_error = str(exc)

    if anomaly_error:
        _set_anomaly_model_error(anomaly_error)

    return {
        "default_model_ready": default_ready,
        "model_path": str(model_path),
        "last_error": _LAST_DEFAULT_MODEL_ERROR,
        "anomaly_model_ready": anomaly_ready,
        "anomaly_model_path": str(anomaly_path),
        "anomaly_last_error": _LAST_ANOMALY_MODEL_ERROR,
        "default_model_mode": "real",
        "anomaly_model_mode": "real",
        "policy_model_mode": "stub",
    }


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
