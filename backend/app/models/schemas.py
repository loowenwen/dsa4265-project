from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class FieldStatus(str, Enum):
    IDENTIFIED = "identified"
    CANNOT_IDENTIFY = "cannot_identify"


class ProcessRequest(BaseModel):
    annual_income: str | None = Field(default=None, description="Required applicant annual income")
    loan_amount: str | None = Field(default=None, description="Required requested loan amount")
    debt_to_income_ratio: str | None = Field(default=None, description="Required DTI value")
    recent_delinquencies: str | None = Field(default=None, description="Required number of recent delinquencies")
    employment_length_months: str | None = Field(default=None, description="Required employment length")
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
    annual_income: float
    loan_amount: float
    debt_to_income_ratio: float
    recent_delinquencies: int
    employment_length_months: int
    demographic_information: str | Literal["cannot identify"]


class ProcessResponse(BaseModel):
    feature_vector: FeatureVector
    normalized_fields: dict[str, NormalizedField]
    missing_fields: list[str]
    suspicious_fields: list[SuspiciousField]
    default_model_output: DefaultModelOutput | None = None
    anomaly_model_output: AnomalyModelOutput | None = None
    policy_retrieval_output: PolicyRetrievalOutput | None = None
    orchestrator_output: OrchestratorOutput | None = None

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
    applicant_processor_output: ProcessResponse
    default_model_output: DefaultModelOutput | None = None
    anomaly_model_output: AnomalyModelOutput | None = None
    policy_retrieval_output: PolicyRetrievalOutput | None = None
    orchestrator_output: OrchestratorOutput | None = None


class ExplanationKeyMetrics(BaseModel):
    probability_of_default: float | None = None
    anomaly_score: float | None = None
    risk_band: str | None = None
    anomaly_band: str | None = None


class ExplanationResponse(BaseModel):
    application_id: str | None = None
    recommended_action: Literal["accept", "reject", "manual review"]
    key_metrics: ExplanationKeyMetrics
    reasons: str
    reason_codes: list[str] = []
    policy_references: list[str] = []
    decision_path: str | None = None
    limitations: list[str] = []
