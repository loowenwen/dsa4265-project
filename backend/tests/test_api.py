import unittest
import csv
import json
import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    AnomalyModelOutput,
    DefaultModelOutput,
)
from app.services.exceptions import ModelUnavailableError


class ApiTests(unittest.TestCase):
    ACCEPT_SAMPLE_PAYLOAD = {
        "person_age": "36",
        "person_income": "120000",
        "person_home_ownership": "MORTGAGE",
        "person_emp_length": "9 years",
        "loan_intent": "HOMEIMPROVEMENT",
        "loan_grade": "A",
        "loan_amnt": "9000",
        "loan_int_rate": "7.2%",
        "loan_percent_income": "7%",
        "cb_person_default_on_file": "N",
        "cb_person_cred_hist_length": "12",
    }

    MANUAL_SAMPLE_PAYLOAD = {
        "person_age": "29",
        "person_income": "42000",
        "person_home_ownership": "RENT",
        "person_emp_length": "1 year",
        "loan_intent": "PERSONAL",
        "loan_grade": "D",
        "loan_amnt": "18000",
        "loan_int_rate": "15.5%",
        "loan_percent_income": "46%",
        "cb_person_default_on_file": "N",
        "cb_person_cred_hist_length": "4",
    }

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

    def test_process_accept_sample_yields_approve(self) -> None:
        sample_path = Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples" / "accept_application.json"
        payload = (
            json.loads(sample_path.read_text(encoding="utf-8"))
            if sample_path.exists()
            else dict(self.ACCEPT_SAMPLE_PAYLOAD)
        )

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
            with patch(
                "app.api.v1.process.providers.get_default_model_output",
                return_value=DefaultModelOutput(
                    model_name="credit_risk_predictor",
                    default_probability=0.02,
                    risk_band="low",
                    top_features=[],
                ),
            ):
                with patch(
                    "app.api.v1.process.providers.get_anomaly_model_output",
                    return_value=AnomalyModelOutput(
                        model_name="ae_agent_autoencoder",
                        anomaly_score=0.05,
                        anomaly_band="normal",
                        out_of_distribution=False,
                        top_anomaly_reasons=[],
                    ),
                ):
                    response = self.client.post("/api/v1/process", json=payload)

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["rule_decision"]["decision"], "APPROVE")
        self.assertEqual(result["ai_decision"]["decision"], "APPROVE")
        self.assertEqual(result["decision_payload"]["overall_decision"]["decision"], "accept")

    def test_process_manual_sample_yields_manual_review(self) -> None:
        sample_path = Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples" / "manual_application.csv"
        if sample_path.exists():
            with sample_path.open("r", encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
        else:
            row = dict(self.MANUAL_SAMPLE_PAYLOAD)

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
            with patch(
                "app.api.v1.process.providers.get_default_model_output",
                return_value=DefaultModelOutput(
                    model_name="credit_risk_predictor",
                    default_probability=0.37,
                    risk_band="medium",
                    top_features=[],
                ),
            ):
                with patch(
                    "app.api.v1.process.providers.get_anomaly_model_output",
                    return_value=AnomalyModelOutput(
                        model_name="ae_agent_autoencoder",
                        anomaly_score=0.17,
                        anomaly_band="high",
                        out_of_distribution=True,
                        top_anomaly_reasons=[],
                    ),
                ):
                    response = self.client.post("/api/v1/process", json=row)

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["rule_decision"]["decision"], "MANUAL_REVIEW")
        self.assertEqual(result["ai_decision"]["decision"], "MANUAL_REVIEW")
        self.assertEqual(result["decision_payload"]["overall_decision"]["decision"], "manual_review")

    def test_process_reject_sample_yields_reject(self) -> None:
        # Matches the record in frontend/public/samples/rejects_application.xlsx.
        payload = {
            "person_age": "22",
            "person_income": "25000",
            "person_home_ownership": "RENT",
            "person_emp_length": "4 months",
            "loan_intent": "PERSONAL",
            "loan_grade": "G",
            "loan_amnt": "30000",
            "loan_int_rate": "21%",
            "loan_percent_income": "95%",
            "cb_person_default_on_file": "Y",
            "cb_person_cred_hist_length": "1",
        }

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
            with patch(
                "app.api.v1.process.providers.get_default_model_output",
                return_value=DefaultModelOutput(
                    model_name="credit_risk_predictor",
                    default_probability=0.99,
                    risk_band="high",
                    top_features=[],
                ),
            ):
                with patch(
                    "app.api.v1.process.providers.get_anomaly_model_output",
                    return_value=AnomalyModelOutput(
                        model_name="ae_agent_autoencoder",
                        anomaly_score=0.27,
                        anomaly_band="high",
                        out_of_distribution=True,
                        top_anomaly_reasons=[],
                    ),
                ):
                    response = self.client.post("/api/v1/process", json=payload)

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["rule_decision"]["decision"], "REJECT")
        self.assertEqual(result["ai_decision"]["decision"], "REJECT")
        self.assertEqual(result["decision_payload"]["overall_decision"]["decision"], "reject")

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
