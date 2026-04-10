from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class FieldStatus(str, Enum):
    IDENTIFIED = "identified"
    CANNOT_IDENTIFY = "cannot_identify"


class ProcessRequest(BaseModel):
    # New schema aligned to model artifact
    person_age: str | None = Field(default=None, description="Applicant age")
    person_income: str | None = Field(default=None, description="Annual income")
    person_home_ownership: str | None = Field(default=None, description="Home ownership status (RENT/OWN/MORTGAGE/OTHER)")
    person_emp_length: str | None = Field(default=None, description="Employment length in years or months")
    loan_intent: str | None = Field(default=None, description="Loan intent category")
    loan_grade: str | None = Field(default=None, description="Loan grade (A-G)")
    loan_amnt: str | None = Field(default=None, description="Loan amount requested")
    loan_int_rate: str | None = Field(default=None, description="Loan interest rate %")
    loan_percent_income: str | None = Field(default=None, description="Loan percent of income (0-1 or %)")
    cb_person_default_on_file: str | None = Field(default=None, description="Y/N for past default on file")
    cb_person_cred_hist_length: str | None = Field(default=None, description="Credit history length (years)")
    additional_information: str | None = Field(default=None, description="Optional free-form applicant notes")


class NormalizedField(BaseModel):
    value: str | float | int
    status: FieldStatus
    source_text: str | None = None


class SuspiciousField(BaseModel):
    field: str
    reason: str
    severity: Literal["low", "medium", "high"]


class FeatureVector(BaseModel):
    person_age: float
    person_income: float
    person_home_ownership: str
    person_emp_length: float  # in years
    loan_intent: str
    loan_grade: str
    loan_amnt: float
    loan_int_rate: float
    loan_percent_income: float
    cb_person_default_on_file: str
    cb_person_cred_hist_length: float


class ProcessResponse(BaseModel):
    feature_vector: FeatureVector
    normalized_fields: dict[str, NormalizedField]
    missing_fields: list[str]
    suspicious_fields: list[SuspiciousField]
    default_model_output: DefaultModelOutput | None = None
    anomaly_model_output: AnomalyModelOutput | None = None
    policy_retrieval_output: PolicyRetrievalOutput | None = None
    orchestrator_output: OrchestratorOutput | None = None  # legacy
    # New dual-decision fields
    rule_decision: RuleDecision | None = None
    ai_decision: AIDecision | None = None
    decision_alignment: DecisionAlignment | None = None
    policy_support: PolicySupport | None = None
    explanation: ExplanationMemo | None = None
    decision_payload: ConsolidatedDecisionPayload | None = None

from typing import Literal
from pydantic import BaseModel


class TopFeature(BaseModel):
    feature: str
    value: str | float | int | None = None
    direction: Literal["increase_risk", "decrease_risk", "unknown"] = "unknown"
    importance: float | None = None
    training_percentile: float | None = None


class DefaultModelOutput(BaseModel):
    model_name: str | None = None
    default_probability: float | None = None
    risk_band: str | None = None
    confidence: float | None = None
    in_distribution: bool | None = None
    top_features: list[TopFeature] = []


class AnomalyReason(BaseModel):
    feature: str
    value: str | float | int | None = None
    reason: str | None = None
    expected_range: str | None = None
    severity: Literal["low", "medium", "high"] | None = None


class AnomalyModelOutput(BaseModel):
    model_name: str | None = None
    anomaly_score: float | None = None
    anomaly_band: str | None = None
    out_of_distribution: bool | None = None
    top_anomaly_reasons: list[AnomalyReason] = []


class PolicyMatch(BaseModel):
    rule_id: str | None = None
    title: str | None = None
    snippet: str
    matched: bool = True
    match_reason: str | None = None
    severity: Literal["hard_stop", "review", "info"] | None = None


class PolicyRetrievalOutput(BaseModel):
    retrieved_rules: list[PolicyMatch] = []


class DataQuality(BaseModel):
    missing_required_fields: list[str] | None = None
    suspicious_fields: list[str] | None = None
    parse_warnings: list[str] | None = None
    is_complete: bool | None = None


class OrchestratorInput(BaseModel):
    applicant: dict
    risk: "DefaultModelOutput"
    anomaly: "AnomalyModelOutput"
    policy: "PolicyRetrievalOutput"
    data_quality: "DataQuality"


class OrchestratorOutput(BaseModel):
    recommendation: Literal["APPROVE", "MANUAL_REVIEW", "REJECT"] | None = None
    decision_path: str | None = None
    reason_codes: list[str] = []
    summary: str | None = None
    evidence: OrchestratorEvidence | None = None


class RuleDecision(BaseModel):
    decision: Literal["APPROVE", "REJECT", "MANUAL_REVIEW"]
    reasons: list[str] = []
    triggered_rules: list[str] = []
    missing_info: list[str] = []
    confidence: float | None = None


class AIDecision(BaseModel):
    decision: Literal["APPROVE", "REJECT", "MANUAL_REVIEW"]
    confidence: float | None = None
    reasons: list[str] = []
    missing_info: list[str] = []
    policy_considerations: list[str] = []


class DecisionAlignment(BaseModel):
    status: Literal["AGREE", "DISAGREE"]
    note: str | None = None


class PolicySupport(BaseModel):
    available: bool = False
    snippets: list[str] = []


class ExplanationMemo(BaseModel):
    memo: str
    summary: str | None = None


class OrchestratorEvidence(BaseModel):
    default_probability: float | None = None
    anomaly_score: float | None = None
    violated_policy_titles: list[str] | None = None
    missing_required_fields: list[str] | None = None
    top_features: list[TopFeature] | None = None
    policy_review_required: bool | None = None
    policy_hard_stop: bool | None = None


class ExplanationRequest(BaseModel):
    application_id: str | None = None
    decision_payload: ConsolidatedDecisionPayload


class ExplanationKeyMetrics(BaseModel):
    probability_of_default: float | None = None
    anomaly_score: float | None = None
    risk_band: str | None = None
    anomaly_band: str | None = None


class ExplanationResponse(BaseModel):
    application_id: str | None = None
    overall_decision: Literal["accept", "reject", "manual_review"]
    key_metrics: ExplanationKeyMetrics
    summary: str
    supporting_evidence: list[ExplanationEvidenceItem] = []
    cautionary_evidence: list[ExplanationEvidenceItem] = []
    limitations: list[str] = []


class DecisionLabelFeature(BaseModel):
    feature: str
    value: str | float | int | None = None
    contribution: float | None = None
    direction: Literal["increase_risk", "decrease_risk", "unknown"] = "unknown"
    reason: str | None = None


class OverallDecisionPayload(BaseModel):
    decision: Literal["accept", "reject", "manual_review"]
    decision_source: str = "decision_maker"
    decision_note: str


class DefaultRiskPayload(BaseModel):
    decision: Literal["accept", "reject", "manual_review"]
    default_probability: float | None = None
    risk_band: str | None = None
    top_features: list[DecisionLabelFeature] = []


class AnomalyDetectionPayload(BaseModel):
    decision: Literal["accept", "reject", "manual_review"]
    anomaly_score: float | None = None
    anomaly_band: str | None = None
    top_features: list[DecisionLabelFeature] = []


class AIDecisionPayload(BaseModel):
    decision: Literal["accept", "reject", "manual_review"]
    top_reasons: list[str] = []
    raw_input: dict


class ConsolidatedDecisionPayload(BaseModel):
    overall_decision: OverallDecisionPayload
    default_risk: DefaultRiskPayload
    anomaly_detection: AnomalyDetectionPayload
    ai_decision: AIDecisionPayload


class ExplanationEvidenceItem(BaseModel):
    text: str
    sources: list[Literal["default_risk", "anomaly_detection", "ai_decision"]] = []
