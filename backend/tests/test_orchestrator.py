import unittest

from app.models.schemas import AIDecision, AnomalyModelOutput, DefaultModelOutput, TopFeature
from app.services.decisioning.decision_payload_builder import build_consolidated_decision_payload


class DecisionPayloadBuilderTests(unittest.TestCase):
    def test_build_payload_creates_hardcoded_agreement_note(self):
        payload = build_consolidated_decision_payload(
            raw_input={
                "person_age": 35,
                "person_income": 85000,
                "person_home_ownership": "RENT",
                "person_emp_length": 6,
                "loan_intent": "EDUCATION",
                "loan_grade": "C",
                "loan_amnt": 12000,
                "loan_int_rate": 11.5,
                "loan_percent_income": 0.1,
            },
            default_model_output=DefaultModelOutput(
                default_probability=0.34,
                risk_band="medium",
                top_features=[
                    TopFeature(
                        feature="loan_grade",
                        value="C",
                        direction="increase_risk",
                        importance=0.16,
                    )
                ],
            ),
            anomaly_model_output=AnomalyModelOutput(
                anomaly_score=0.18,
                anomaly_band="normal",
                top_anomaly_reasons=[],
            ),
            ai_decision=AIDecision(
                decision="MANUAL_REVIEW",
                reasons=["Moderate repayment risk."],
                missing_info=[],
                policy_considerations=[],
            ),
            decisions={
                "default_risk_decision": "manual_review",
                "anomaly_decision": "accept",
                "ai_decision_label": "manual_review",
                "overall_decision": "manual_review",
                "decision_note": "Default risk and AI decision suggest manual review, while anomaly detection suggests accept.",
            },
        )

        self.assertEqual(payload.overall_decision.decision, "manual_review")
        self.assertIn("Default risk and AI decision suggest manual review", payload.overall_decision.decision_note)
        self.assertEqual(payload.ai_decision.raw_input["person_income"], 85000)
        self.assertEqual(payload.default_risk.top_features[0].feature, "loan_grade")


if __name__ == "__main__":
    unittest.main()
