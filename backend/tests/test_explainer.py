import unittest
from unittest.mock import Mock, patch

from app.models.schemas import (
    AIDecisionPayload,
    AnomalyDetectionPayload,
    ConsolidatedDecisionPayload,
    DecisionLabelFeature,
    DefaultRiskPayload,
    ExplanationRequest,
    OverallDecisionPayload,
)
from app.services.explainer import build_explanation


class ExplainerTests(unittest.TestCase):
    def _decision_payload(self) -> ConsolidatedDecisionPayload:
        return ConsolidatedDecisionPayload(
            overall_decision=OverallDecisionPayload(
                decision="manual_review",
                decision_note=(
                    "Default risk and AI decision suggest manual review, while anomaly "
                    "detection suggests accept."
                ),
            ),
            default_risk=DefaultRiskPayload(
                decision="manual_review",
                default_probability=0.34,
                risk_band="medium",
                top_features=[
                    DecisionLabelFeature(
                        feature="loan_grade",
                        value="C",
                        contribution=0.16,
                        direction="increase_risk",
                    )
                ],
            ),
            anomaly_detection=AnomalyDetectionPayload(
                decision="accept",
                anomaly_score=0.18,
                anomaly_band="normal",
                top_features=[
                    DecisionLabelFeature(
                        feature="person_emp_length",
                        value=6,
                        reason="Employment length is within the normal range for similar applicants",
                    )
                ],
            ),
            ai_decision=AIDecisionPayload(
                decision="manual_review",
                top_reasons=[
                    "The applicant shows moderate repayment risk based on loan grade and interest rate."
                ],
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
            ),
        )

    def test_build_explanation_returns_unavailable_without_api_key(self):
        response = build_explanation(
            ExplanationRequest(application_id="app-123", decision_payload=self._decision_payload())
        )

        self.assertEqual(response.overall_decision, "manual_review")
        self.assertEqual(response.key_metrics.probability_of_default, 0.34)
        self.assertEqual(response.key_metrics.anomaly_score, 0.18)
        self.assertIn("Explanation unavailable", response.summary)
        self.assertEqual(response.supporting_evidence, [])
        self.assertEqual(response.cautionary_evidence, [])

    @patch("app.services.explainer.httpx.post")
    @patch("app.services.explainer.settings.OPENROUTER_API_KEY", "test-key")
    def test_build_explanation_uses_llm_when_response_is_grounded(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"summary":"The application shows some stable signals, but the overall '
                            'decision remains manual review because the risk assessment and AI review '
                            'both indicate moderate caution.","supporting_evidence":[{"text":"Employment '
                            'length is 6 and appears consistent with similar applicants.","sources":["anomaly_detection"]}],'
                            '"cautionary_evidence":[{"text":"Default probability is 0.34 and the loan grade C '
                            'contributes to moderate risk.","sources":["default_risk","ai_decision"]}]}'
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        response = build_explanation(
            ExplanationRequest(application_id="app-456", decision_payload=self._decision_payload())
        )

        self.assertIn("manual review", response.summary.lower())
        self.assertEqual(len(response.supporting_evidence), 1)
        self.assertEqual(response.supporting_evidence[0].sources, ["anomaly_detection"])
        self.assertEqual(len(response.cautionary_evidence), 1)
        self.assertIn("default_risk", response.cautionary_evidence[0].sources)
        self.assertEqual(response.limitations, [])

    @patch("app.services.explainer.httpx.post")
    @patch("app.services.explainer.settings.OPENROUTER_API_KEY", "test-key")
    def test_build_explanation_skips_empty_evidence_item_instead_of_failing(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"summary":"Manual review remains appropriate based on the provided risk '
                            'and anomaly signals.","supporting_evidence":[{"text":"",'
                            '"sources":["default_risk"]},{"text":"Anomaly score is 0.18 and indicates '
                            'normal profile distance.","sources":["anomaly_detection"]}],'
                            '"cautionary_evidence":[]}'
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        response = build_explanation(
            ExplanationRequest(application_id="app-790", decision_payload=self._decision_payload())
        )

        self.assertNotIn("Explanation unavailable", response.summary)
        self.assertEqual(len(response.supporting_evidence), 1)
        self.assertEqual(response.supporting_evidence[0].sources, ["anomaly_detection"])
        self.assertEqual(response.limitations, [])

    @patch("app.services.explainer.httpx.post")
    @patch("app.services.explainer.settings.OPENROUTER_API_KEY", "test-key")
    def test_build_explanation_returns_unavailable_when_llm_hallucinates_number(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"summary":"The application should be reviewed because the risk score is 0.99.",'
                            '"supporting_evidence":[],"cautionary_evidence":[]}'
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        response = build_explanation(
            ExplanationRequest(application_id="app-789", decision_payload=self._decision_payload())
        )

        self.assertIn("Explanation unavailable", response.summary)
        self.assertTrue(response.limitations)


if __name__ == "__main__":
    unittest.main()
