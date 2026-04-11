import unittest
from unittest.mock import patch

import numpy as np

from app.services.credit_risk_predictor import predict_one_record


class _FakeModel:
    def predict_proba(self, _scored_input):
        return np.array([[0.2, 0.8]])


class CreditRiskPredictorTests(unittest.TestCase):
    def test_predict_one_record_survives_shap_failure(self) -> None:
        artifact = {
            "model": _FakeModel(),
            "preprocessor": None,
            "feature_names": None,
            "training_background": None,
        }
        new_record = {
            "person_age": 35,
            "person_income": 85000,
            "person_home_ownership": "RENT",
            "person_emp_length": 6,
            "loan_intent": "EDUCATION",
            "loan_grade": "C",
            "loan_amnt": 12000,
            "loan_int_rate": 11.5,
            "loan_percent_income": 0.1,
            "cb_person_default_on_file": "N",
            "cb_person_cred_hist_length": 8,
        }

        with patch("app.services.credit_risk_predictor.joblib.load", return_value=artifact):
            with patch("app.services.credit_risk_predictor.shap.TreeExplainer", side_effect=RuntimeError("boom")):
                output = predict_one_record("fake-model-path", new_record, top_n=3)

        self.assertEqual(output["default_probability"], 0.8)
        self.assertEqual(output["risk_level"], "high")
        self.assertEqual(output["top_features"], [])


if __name__ == "__main__":
    unittest.main()

