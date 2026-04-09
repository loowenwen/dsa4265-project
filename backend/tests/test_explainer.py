import unittest

from app.models.schemas import (
    AnomalyModelOutput,
    AnomalyReason,
    DefaultModelOutput,
    ExplanationRequest,
    OrchestratorEvidence,
    OrchestratorOutput,
    PolicyMatch,
    PolicyRetrievalOutput,
    ProcessResponse,
    SuspiciousField,
    TopFeature,
)
from app.services.explainer import build_explanation


class ExplainerTests(unittest.TestCase):
    def _process_response(self) -> ProcessResponse:
        return ProcessResponse(
            feature_vector={
                "annual_income": 42000,
                "loan_amount": 18000,
                "debt_to_income_ratio": 46,
                "recent_delinquencies": 2,
                "employment_length_months": 8,
                "demographic_information": "cannot identify",
            },
            normalized_fields={},
            missing_fields=[],
            suspicious_fields=[
                SuspiciousField(
                    field="debt_to_income_ratio",
                    reason="Value exceeds the normal range for automatic approval.",
                    severity="medium",
                )
            ],
        )

    def test_build_explanation_uses_orchestrator_recommendation_and_clean_report(self):
        payload = ExplanationRequest(
            application_id="app-123",
            applicant_processor_output=self._process_response(),
            default_model_output=DefaultModelOutput(
                default_probability=0.37,
                risk_band="medium",
                top_features=[
                    TopFeature(
                        feature="debt_to_income_ratio",
                        value=46,
                        direction="increase_risk",
                    )
                ],
            ),
            anomaly_model_output=AnomalyModelOutput(
                anomaly_score=0.61,
                anomaly_band="elevated",
                out_of_distribution=True,
                top_anomaly_reasons=[
                    AnomalyReason(
                        feature="employment_length_months",
                        reason="short employment history relative to requested loan",
                    )
                ],
            ),
            policy_retrieval_output=PolicyRetrievalOutput(
                retrieved_rules=[
                    PolicyMatch(
                        rule_id="POL-001",
                        title="High DTI requires manual review",
                        snippet="Applicants with debt-to-income ratio above 45% require manual review.",
                        severity="review",
                    )
                ]
            ),
            orchestrator_output=OrchestratorOutput(
                recommendation="MANUAL_REVIEW",
                decision_path="manual_review -> review_flags",
                reason_codes=["POLICY_REVIEW_TRIGGER", "ELEVATED_ANOMALY"],
                summary="The case should be escalated because policy review is triggered and anomaly is elevated.",
                evidence=OrchestratorEvidence(
                    default_probability=0.37,
                    anomaly_score=0.61,
                    violated_policy_titles=["High DTI requires manual review"],
                ),
            ),
        )

        response = build_explanation(payload)

        self.assertEqual(response.recommended_action, "manual review")
        self.assertEqual(response.key_metrics.probability_of_default, 0.37)
        self.assertEqual(response.key_metrics.anomaly_score, 0.61)
        self.assertIn("probability of default is 0.37", response.reasons)
        self.assertIn("anomaly score is 0.61", response.reasons)
        self.assertIn("High DTI requires manual review", response.reasons)
        self.assertEqual(response.reason_codes, ["POLICY_REVIEW_TRIGGER", "ELEVATED_ANOMALY"])
        self.assertEqual(response.policy_references, ["High DTI requires manual review"])

    def test_build_explanation_defaults_to_manual_review_without_orchestrator(self):
        payload = ExplanationRequest(
            application_id="app-456",
            applicant_processor_output=self._process_response(),
            default_model_output=DefaultModelOutput(default_probability=None, top_features=[]),
            anomaly_model_output=AnomalyModelOutput(anomaly_score=None, top_anomaly_reasons=[]),
            policy_retrieval_output=PolicyRetrievalOutput(retrieved_rules=[]),
        )

        response = build_explanation(payload)

        self.assertEqual(response.recommended_action, "manual review")
        self.assertIsNone(response.key_metrics.probability_of_default)
        self.assertIsNone(response.key_metrics.anomaly_score)
        self.assertTrue(response.limitations)


if __name__ == "__main__":
    unittest.main()
