import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.valid_payload = {
            "annual_income": "$42,000",
            "loan_amount": "18000",
            "debt_to_income_ratio": "46%",
            "recent_delinquencies": "2",
            "employment_length_months": "8 months",
            "additional_information": "Applicant Summary: no additional demographic details.",
        }

    def test_health(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_process_success(self) -> None:
        response = self.client.post("/api/v1/process", json=self.valid_payload)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["feature_vector"]["annual_income"], 42000.0)
        self.assertEqual(payload["feature_vector"]["loan_amount"], 18000.0)
        self.assertEqual(payload["feature_vector"]["debt_to_income_ratio"], 46.0)
        self.assertEqual(payload["feature_vector"]["recent_delinquencies"], 2)
        self.assertEqual(payload["feature_vector"]["employment_length_months"], 8)
        self.assertEqual(payload["feature_vector"]["demographic_information"], "cannot identify")

        self.assertIn("demographic_information", payload["missing_fields"])
        self.assertEqual(payload["suspicious_fields"][0]["field"], "debt_to_income_ratio")

    def test_process_missing_required_field(self) -> None:
        payload = dict(self.valid_payload)
        payload.pop("loan_amount")

        response = self.client.post("/api/v1/process", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn(
            {"field": "loan_amount", "message": "Required field is missing or invalid"},
            response.json()["detail"],
        )

    def test_process_malformed_required_field(self) -> None:
        payload = dict(self.valid_payload)
        payload["loan_amount"] = "eighteen thousand"

        response = self.client.post("/api/v1/process", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn(
            {"field": "loan_amount", "message": "Required field is missing or invalid"},
            response.json()["detail"],
        )


if __name__ == "__main__":
    unittest.main()
