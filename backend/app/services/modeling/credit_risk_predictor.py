import logging
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def preprocess_prediction_record(new_record: dict) -> pd.DataFrame:
    df = pd.DataFrame([new_record]).copy()

    object_cols = df.select_dtypes(include="object").columns.tolist()
    for col in object_cols:
        df[col] = df[col].astype(str).str.strip().str.upper()

    if "person_emp_length" in df.columns:
        df["person_emp_length_missing_flag"] = df["person_emp_length"].isna().astype(int)
    else:
        df["person_emp_length"] = np.nan
        df["person_emp_length_missing_flag"] = 1

    if "loan_int_rate" in df.columns:
        df["loan_int_rate_missing_flag"] = df["loan_int_rate"].isna().astype(int)
    else:
        df["loan_int_rate"] = np.nan
        df["loan_int_rate_missing_flag"] = 1

    required_numeric = [
        "person_age",
        "person_income",
        "person_emp_length",
        "loan_amnt",
        "loan_int_rate",
        "loan_percent_income",
        "cb_person_cred_hist_length",
    ]
    for col in required_numeric:
        if col not in df.columns:
            df[col] = np.nan

    df.loc[df["person_age"] > 80, "person_age"] = np.nan
    df.loc[df["person_emp_length"] > 60, "person_emp_length"] = np.nan

    df["log_person_income"] = np.log1p(df["person_income"])
    df["log_loan_amnt"] = np.log1p(df["loan_amnt"])
    df["loan_to_income_ratio_check"] = df["loan_amnt"] / df["person_income"].replace(0, np.nan)
    df["credit_history_to_age_ratio"] = (
        df["cb_person_cred_hist_length"] / df["person_age"].replace(0, np.nan)
    )

    return df


def _patch_imputers(obj):
    """
    Patch SimpleImputer instances saved under older sklearn so they work on newer versions.
    """
    if isinstance(obj, SimpleImputer):
        if not hasattr(obj, "_fill_dtype"):
            try:
                obj._fill_dtype = obj.statistics_.dtype
            except Exception:
                obj._fill_dtype = None
        if not hasattr(obj, "_fit_dtype"):
            try:
                obj._fit_dtype = obj.statistics_.dtype
            except Exception:
                obj._fit_dtype = None
        if not hasattr(obj, "_fill_value"):
            try:
                obj._fill_value = obj.statistics_
            except Exception:
                obj._fill_value = None
    elif isinstance(obj, Pipeline):
        for _, step in obj.steps:
            _patch_imputers(step)
    elif isinstance(obj, ColumnTransformer):
        for _, transformer, _cols in obj.transformers:
            _patch_imputers(transformer)
        if hasattr(obj, "transformers_"):
            for _, transformer, _cols in obj.transformers_:
                _patch_imputers(transformer)


def _make_positive_class_explanation(
    explainer: shap.TreeExplainer,
    transformed_row,
    feature_names: List[str],
):
    shap_values = explainer.shap_values(transformed_row)
    expected_value = explainer.expected_value

    if isinstance(shap_values, list):
        values = np.asarray(shap_values[1])[0]
        base_value = expected_value[1] if isinstance(expected_value, (list, np.ndarray)) else expected_value
    else:
        shap_values = np.asarray(shap_values)
        if shap_values.ndim == 3:
            values = shap_values[0, :, 1]
            base_value = expected_value[1] if isinstance(expected_value, (list, np.ndarray)) else expected_value
        else:
            values = shap_values[0]
            base_value = expected_value

    return shap.Explanation(
        values=values,
        base_values=float(np.asarray(base_value).reshape(-1)[0]),
        data=np.asarray(transformed_row)[0],
        feature_names=feature_names,
    )


def _group_one_hot_features(
    explanation: shap.Explanation,
    raw_row: pd.DataFrame,
) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}

    for i, feature_name in enumerate(explanation.feature_names):
        original_name = feature_name

        if feature_name.startswith("num__"):
            original_name = feature_name.replace("num__", "", 1)
        elif feature_name.startswith("cat__"):
            encoded = feature_name.replace("cat__", "", 1)
            matched = None
            for raw_col in raw_row.columns:
                if encoded == raw_col or encoded.startswith(f"{raw_col}_"):
                    matched = raw_col
                    break
            original_name = matched if matched is not None else encoded

        contribution = float(explanation.values[i])
        raw_value = raw_row.iloc[0][original_name] if original_name in raw_row.columns else None

        if original_name not in grouped:
            grouped[original_name] = {
                "feature": original_name,
                "feature_value": None if pd.isna(raw_value) else raw_value,
                "contribution_to_probability": 0.0,
            }

        grouped[original_name]["contribution_to_probability"] += contribution

    grouped_list = []
    for item in grouped.values():
        item["effect"] = "increase_risk" if item["contribution_to_probability"] >= 0 else "decrease_risk"
        item["abs_contribution"] = abs(item["contribution_to_probability"])
        grouped_list.append(item)

    grouped_list.sort(key=lambda x: x["abs_contribution"], reverse=True)
    return grouped_list


def _get_risk_level(probability: float) -> str:
    if probability < 0.3:
        return "low"
    if probability < 0.5:
        return "medium"
    return "high"


def _load_artifact(model_path: str) -> dict:
    artifact = joblib.load(model_path)
    required_keys = {"model", "preprocessor"}
    missing_keys = required_keys - set(artifact.keys())
    if missing_keys:
        raise ValueError(f"Model artifact missing required keys: {sorted(missing_keys)}")
    return artifact


def verify_model_artifact(model_path: str) -> None:
    """Validate that the serialized model artifact is loadable and has expected keys."""
    _load_artifact(model_path)


def predict_one_record(model_path: str, new_record: Dict[str, Any], top_n: int = 5) -> Dict[str, Any]:
    artifact = _load_artifact(model_path)
    model = artifact["model"]
    preprocessor = artifact["preprocessor"]
    feature_names = artifact.get("feature_names")
    training_background = artifact.get("training_background")

    raw_row = preprocess_prediction_record(new_record)

    if preprocessor is not None:
        _patch_imputers(preprocessor)
        _patch_imputers(model)
        expected_columns = list(preprocessor.feature_names_in_)
        for col in expected_columns:
            if col not in raw_row.columns:
                raw_row[col] = np.nan
        raw_row = raw_row[expected_columns]

        transformed_row = preprocessor.transform(raw_row)
        scored_input = transformed_row

        if feature_names is None:
            feature_names = preprocessor.get_feature_names_out().tolist()
    else:
        transformed_row = raw_row.values
        scored_input = raw_row
        if feature_names is None:
            feature_names = raw_row.columns.tolist()

    probability = float(model.predict_proba(scored_input)[:, 1][0])
    predicted_class = int(probability >= 0.5)
    risk_level = _get_risk_level(probability)

    top_features: list[dict[str, Any]] = []
    try:
        if training_background is not None:
            if preprocessor is not None:
                background_processed = training_background.copy()
                for col in expected_columns:
                    if col not in background_processed.columns:
                        background_processed[col] = np.nan
                background_processed = background_processed[expected_columns]
                shap_background = preprocessor.transform(background_processed)
            else:
                shap_background = training_background.values
        else:
            shap_background = transformed_row

        explainer = shap.TreeExplainer(model, data=shap_background, model_output="probability")
        explanation = _make_positive_class_explanation(explainer, transformed_row, feature_names)

        grouped_features = _group_one_hot_features(explanation, raw_row)
        top_features = [
            {
                "feature": item["feature"],
                "feature_value": item["feature_value"],
                "effect": item["effect"],
                "contribution_to_probability": round(float(item["contribution_to_probability"]), 6),
            }
            for item in grouped_features[:top_n]
        ]
    except Exception as exc:
        # Keep prediction available even when explainability stack fails.
        logger.warning("[credit_risk_predictor] SHAP explainability unavailable: %s", exc)

    return {
        "default_probability": round(probability, 6),
        "predicted_class": predicted_class,
        "risk_level": risk_level,
        "top_features": top_features,
    }
