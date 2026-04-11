import tempfile
import unittest
import types
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services import providers
from app.services.exceptions import ModelUnavailableError


class ProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feature_vector = SimpleNamespace(
            person_age=35.0,
            person_income=85000.0,
            person_home_ownership="RENT",
            person_emp_length=6.0,
            loan_intent="EDUCATION",
            loan_grade="C",
            loan_amnt=12000.0,
            loan_int_rate=11.5,
            loan_percent_income=0.1,
            cb_person_default_on_file="N",
            cb_person_cred_hist_length=8.0,
        )

    def test_get_default_model_output_success(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".joblib") as tmp_file:
            with patch("app.services.modeling.providers._resolve_model_path", return_value=Path(tmp_file.name)):
                fake_predictor = types.ModuleType("app.services.modeling.credit_risk_predictor")
                fake_predictor.predict_one_record = lambda *_args, **_kwargs: {
                    "default_probability": 0.42,
                    "risk_level": "medium",
                    "top_features": [
                        {
                            "feature": "loan_grade",
                            "feature_value": "C",
                            "effect": "increase_risk",
                            "contribution_to_probability": 0.18,
                        }
                    ],
                }
                with patch.dict(sys.modules, {"app.services.modeling.credit_risk_predictor": fake_predictor}):
                    output = providers.get_default_model_output(self.feature_vector)

        self.assertEqual(output.model_name, "credit_risk_predictor")
        self.assertIsNotNone(output.default_probability)
        self.assertEqual(output.default_probability, 0.42)
        self.assertEqual(output.risk_band, "medium")
        self.assertEqual(len(output.top_features), 1)
        self.assertEqual(output.top_features[0].feature, "loan_grade")

    def test_get_default_model_output_raises_when_artifact_missing(self) -> None:
        with patch(
            "app.services.modeling.providers._resolve_model_path",
            return_value=Path("/tmp/does-not-exist.joblib"),
        ):
            with self.assertRaises(ModelUnavailableError):
                providers.get_default_model_output(self.feature_vector)

    def test_get_anomaly_model_output_success(self) -> None:
        fake_prediction = {
            "anomaly_score": 0.61,
            "is_anomalous": True,
            "distribution_flag": "out_of_distribution",
            "top_anomalous_features": [
                {"feature": "loan_int_rate", "feature_error": 0.34},
                {"feature": "loan_percent_income", "feature_error": 0.18},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("app.services.modeling.providers._resolve_anomaly_model_dir", return_value=Path(tmp_dir)):
                with patch("app.services.modeling.providers._load_anomaly_artifacts", return_value={"ok": True}):
                    with patch("app.services.modeling.providers._score_anomaly_record", return_value=fake_prediction):
                        output = providers.get_anomaly_model_output(self.feature_vector)

        self.assertEqual(output.model_name, "ae_agent_autoencoder")
        self.assertEqual(output.anomaly_score, 0.61)
        self.assertEqual(output.anomaly_band, "elevated")
        self.assertTrue(output.out_of_distribution)
        self.assertEqual(len(output.top_anomaly_reasons), 2)
        self.assertEqual(output.top_anomaly_reasons[0].feature, "loan_int_rate")

    def test_get_anomaly_model_output_raises_when_artifact_dir_missing(self) -> None:
        with patch(
            "app.services.modeling.providers._resolve_anomaly_model_dir",
            return_value=Path("/tmp/does-not-exist"),
        ):
            with self.assertRaises(ModelUnavailableError):
                providers.get_anomaly_model_output(self.feature_vector)


if __name__ == "__main__":
    unittest.main()
