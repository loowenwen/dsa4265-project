import unittest

from fastapi.testclient import TestClient

from app.main import app


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

    def test_process_success(self) -> None:
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
