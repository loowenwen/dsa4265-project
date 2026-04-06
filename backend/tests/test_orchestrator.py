import unittest

from app.core import decision_config as cfg
from app.models.schemas import (
    AnomalyModelOutput,
    DataQuality,
    DefaultModelOutput,
    OrchestratorInput,
    PolicyMatch,
    PolicyRetrievalOutput,
)
from app.services.orchestrator import decide


class OrchestratorTests(unittest.TestCase):
    def _base_inputs(self):
        applicant = {
            "annual_income": 50000,
            "loan_amount": 10000,
            "debt_to_income_ratio": 20.0,
            "recent_delinquencies": 0,
            "employment_length_months": 24,
        }
        risk = DefaultModelOutput(default_probability=0.1, top_features=[])
        anomaly = AnomalyModelOutput(anomaly_score=0.1)
        policy = PolicyRetrievalOutput(retrieved_rules=[])
        data_quality = DataQuality(missing_required_fields=[], is_complete=True)
        return applicant, risk, anomaly, policy, data_quality

    def test_incomplete_data_manual_review(self):
        applicant, risk, anomaly, policy, data_quality = self._base_inputs()
        data_quality.missing_required_fields = ["annual_income"]
        data_quality.is_complete = False

        output = decide(
            OrchestratorInput(
                applicant=applicant,
                risk=risk,
                anomaly=anomaly,
                policy=policy,
                data_quality=data_quality,
            )
        )
        self.assertEqual(output.recommendation, "MANUAL_REVIEW")
        self.assertIn("INCOMPLETE_DATA", output.reason_codes)

    def test_policy_hard_stop_reject(self):
        applicant, risk, anomaly, _, data_quality = self._base_inputs()
        policy = PolicyRetrievalOutput(
            retrieved_rules=[
                PolicyMatch(rule_id="hs", title="Hard stop", snippet="", severity="hard_stop"),
            ]
        )

        output = decide(
            OrchestratorInput(
                applicant=applicant,
                risk=risk,
                anomaly=anomaly,
                policy=policy,
                data_quality=data_quality,
            )
        )
        self.assertEqual(output.recommendation, "REJECT")
        self.assertIn("POLICY_HARD_STOP", output.reason_codes)

    def test_high_default_probability_reject(self):
        applicant, _, anomaly, policy, data_quality = self._base_inputs()
        risk = DefaultModelOutput(default_probability=cfg.REJECT_THRESHOLD)

        output = decide(
            OrchestratorInput(
                applicant=applicant,
                risk=risk,
                anomaly=anomaly,
                policy=policy,
                data_quality=data_quality,
            )
        )
        self.assertEqual(output.recommendation, "REJECT")
        self.assertIn("HIGH_DEFAULT_RISK", output.reason_codes)

    def test_low_risk_approve(self):
        applicant, risk, anomaly, policy, data_quality = self._base_inputs()
        risk.default_probability = 0.1
        anomaly.anomaly_score = 0.1

        output = decide(
            OrchestratorInput(
                applicant=applicant,
                risk=risk,
                anomaly=anomaly,
                policy=policy,
                data_quality=data_quality,
            )
        )
        self.assertEqual(output.recommendation, "APPROVE")
        self.assertIn("LOW_RISK_CLEAR_POLICY", output.reason_codes)

    def test_elevated_anomaly_manual_review(self):
        applicant, risk, anomaly, policy, data_quality = self._base_inputs()
        anomaly.anomaly_score = cfg.ANOMALY_REVIEW_THRESHOLD

        output = decide(
            OrchestratorInput(
                applicant=applicant,
                risk=risk,
                anomaly=anomaly,
                policy=policy,
                data_quality=data_quality,
            )
        )
        self.assertEqual(output.recommendation, "MANUAL_REVIEW")
        self.assertIn("ELEVATED_ANOMALY", output.reason_codes)


if __name__ == "__main__":
    unittest.main()
