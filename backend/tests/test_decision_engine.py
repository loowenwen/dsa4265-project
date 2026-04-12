import unittest
from unittest.mock import patch

from app.models.schemas import AIDecision
from app.services.decisioning import decision_engine as engine


class RuleVoteBoundaryTests(unittest.TestCase):
    def test_reject_on_default_probability_boundary(self) -> None:
        rule = engine._rule_based_decision(
            default_probability=0.50,
            anomaly_score=0.01,
            missing_fields=[],
            suspicious_fields=[],
        )
        self.assertEqual(rule.decision, "REJECT")

    def test_approve_on_low_default_probability_with_clean_data(self) -> None:
        rule = engine._rule_based_decision(
            default_probability=0.29,
            anomaly_score=0.01,
            missing_fields=[],
            suspicious_fields=[],
        )
        self.assertEqual(rule.decision, "APPROVE")

    def test_manual_review_on_anomaly_boundary(self) -> None:
        rule = engine._rule_based_decision(
            default_probability=0.10,
            anomaly_score=0.1173,
            missing_fields=[],
            suspicious_fields=[],
        )
        self.assertEqual(rule.decision, "MANUAL_REVIEW")

    def test_manual_review_on_suspicious_fields(self) -> None:
        rule = engine._rule_based_decision(
            default_probability=0.10,
            anomaly_score=0.01,
            missing_fields=[],
            suspicious_fields=["loan_percent_income"],
        )
        self.assertEqual(rule.decision, "MANUAL_REVIEW")

    def test_manual_review_on_missing_required_fields(self) -> None:
        rule = engine._rule_based_decision(
            default_probability=0.10,
            anomaly_score=0.01,
            missing_fields=["loan_amnt"],
            suspicious_fields=[],
        )
        self.assertEqual(rule.decision, "MANUAL_REVIEW")
        self.assertIn("loan_amnt", rule.missing_info)

    def test_manual_review_for_uncertain_band(self) -> None:
        rule = engine._rule_based_decision(
            default_probability=0.40,
            anomaly_score=0.01,
            missing_fields=[],
            suspicious_fields=[],
        )
        self.assertEqual(rule.decision, "MANUAL_REVIEW")


class TwoVoteCombinerTests(unittest.TestCase):
    def test_approve_and_approve_returns_approve(self) -> None:
        self.assertEqual(engine._combine_two_votes("accept", "accept"), "accept")

    def test_reject_and_reject_returns_reject(self) -> None:
        self.assertEqual(engine._combine_two_votes("reject", "reject"), "reject")

    def test_approve_and_reject_returns_manual_review(self) -> None:
        self.assertEqual(engine._combine_two_votes("accept", "reject"), "manual_review")

    def test_manual_review_always_returns_manual_review(self) -> None:
        self.assertEqual(engine._combine_two_votes("manual_review", "accept"), "manual_review")
        self.assertEqual(engine._combine_two_votes("reject", "manual_review"), "manual_review")


class EngineAggregationTests(unittest.TestCase):
    def test_run_dual_engine_uses_rule_and_ai_votes_for_overall(self) -> None:
        with patch.object(
            engine,
            "_ai_underwriting_decision",
            return_value=AIDecision(
                decision="REJECT",
                confidence=0.8,
                reasons=["mocked"],
                missing_info=[],
                policy_considerations=[],
            ),
        ):
            _, _, _, decisions = engine.run_dual_engine(
                applicant={"loan_percent_income": 0.1},
                default_probability=0.10,
                anomaly_score=0.01,
                missing_fields=[],
                suspicious_fields=[],
                policy_output=None,
            )

        self.assertEqual(decisions["rule_decision_label"], "accept")
        self.assertEqual(decisions["ai_decision_label"], "reject")
        self.assertEqual(decisions["overall_decision"], "manual_review")
        self.assertIn("Rule vote is accept", decisions["decision_note"])
        self.assertIn("AI vote is reject", decisions["decision_note"])


if __name__ == "__main__":
    unittest.main()
