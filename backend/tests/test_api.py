import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    AnomalyModelOutput,
    DefaultModelOutput,
)
from app.services.exceptions import ModelUnavailableError


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.valid_payload = {
            "person_age": "35",
            "person_income": "85000",
            "person_home_ownership": "RENT",
            "person_emp_length": "6 years",
            "loan_intent": "EDUCATION",
            "loan_grade": "C",
            "loan_amnt": "12000",
            "loan_int_rate": "11.5%",
            "loan_percent_income": "10%",
            "cb_person_default_on_file": "N",
            "cb_person_cred_hist_length": "8",
        }

    def test_health(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_models(self) -> None:
        response = self.client.get("/api/v1/health/models")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("default_model_ready", payload)
        self.assertIn("model_path", payload)
        self.assertIn("last_error", payload)
        self.assertIn("anomaly_model_ready", payload)
        self.assertIn("anomaly_model_path", payload)
        self.assertIn("anomaly_last_error", payload)

    def test_process_success(self) -> None:
        with patch(
            "app.api.v1.process.providers.get_default_model_output",
            return_value=DefaultModelOutput(
                model_name="credit_risk_predictor",
                default_probability=0.42,
                risk_band="medium",
                top_features=[],
            ),
        ):
            with patch(
                "app.api.v1.process.providers.get_anomaly_model_output",
                return_value=AnomalyModelOutput(
                    model_name="ae_agent_autoencoder",
                    anomaly_score=0.18,
                    anomaly_band="normal",
                    out_of_distribution=False,
                    top_anomaly_reasons=[],
                ),
            ):
                response = self.client.post("/api/v1/process", json=self.valid_payload)

        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["feature_vector"]["person_age"], 35.0)
        self.assertEqual(payload["feature_vector"]["person_income"], 85000.0)
        self.assertEqual(payload["feature_vector"]["person_home_ownership"], "RENT")
        self.assertEqual(payload["feature_vector"]["person_emp_length"], 6.0)
        self.assertEqual(payload["feature_vector"]["loan_grade"], "C")
        self.assertEqual(payload["feature_vector"]["loan_amnt"], 12000.0)
        self.assertEqual(payload["feature_vector"]["loan_int_rate"], 11.5)
        self.assertEqual(payload["feature_vector"]["loan_percent_income"], 0.1)
        self.assertEqual(payload["default_model_output"]["model_name"], "credit_risk_predictor")
        self.assertEqual(payload["default_model_output"]["default_probability"], 0.42)
        self.assertEqual(payload["anomaly_model_output"]["model_name"], "ae_agent_autoencoder")
        self.assertEqual(payload["anomaly_model_output"]["anomaly_score"], 0.18)

        self.assertIn("decision_payload", payload)
        self.assertEqual(payload["decision_payload"]["ai_decision"]["raw_input"]["person_income"], 85000.0)

    def test_process_missing_required_field(self) -> None:
        payload = dict(self.valid_payload)
        payload.pop("loan_amnt")

        response = self.client.post("/api/v1/process", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn(
            {"field": "loan_amnt", "message": "Required field is missing or invalid"},
            response.json()["detail"],
        )

    def test_process_returns_503_when_default_model_unavailable(self) -> None:
        with patch(
            "app.api.v1.process.providers.get_default_model_output",
            side_effect=ModelUnavailableError(
                message="Default model runtime dependencies unavailable",
                model_path="app/models/credit_risk_lgbm.joblib",
                cause="No module named 'joblib'",
            ),
        ):
            response = self.client.post("/api/v1/process", json=self.valid_payload)

        self.assertEqual(response.status_code, 503)
        detail = response.json()["detail"]
        self.assertEqual(detail["error_code"], "default_model_unavailable")
        self.assertEqual(detail["model_path"], "app/models/credit_risk_lgbm.joblib")

    def test_process_returns_503_when_anomaly_model_unavailable(self) -> None:
        with patch(
            "app.api.v1.process.providers.get_default_model_output",
            return_value=DefaultModelOutput(
                model_name="credit_risk_predictor",
                default_probability=0.42,
                risk_band="medium",
                top_features=[],
            ),
        ):
            with patch(
                "app.api.v1.process.providers.get_anomaly_model_output",
                side_effect=ModelUnavailableError(
                    message="Anomaly model runtime dependencies unavailable",
                    model_path="app/models/ae_agent",
                    cause="No module named 'torch'",
                ),
            ):
                response = self.client.post("/api/v1/process", json=self.valid_payload)

        self.assertEqual(response.status_code, 503)
        detail = response.json()["detail"]
        self.assertEqual(detail["error_code"], "anomaly_model_unavailable")
        self.assertEqual(detail["model_path"], "app/models/ae_agent")

    def test_process_malformed_required_field(self) -> None:
        payload = dict(self.valid_payload)
        payload["loan_amnt"] = "twelve thousand"

        response = self.client.post("/api/v1/process", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn(
            {"field": "loan_amnt", "message": "Required field is missing or invalid"},
            response.json()["detail"],
        )


if __name__ == "__main__":
    unittest.main()
