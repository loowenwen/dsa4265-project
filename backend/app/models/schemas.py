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


class PolicyRetrievalOutput(BaseModel):
    retrieved_rules: list[PolicyMatch] = []


class OrchestratorOutput(BaseModel):
    recommended_action: Literal["approve", "manual_review", "reject"] | None = None
    decision_reasons: list[str] = []


class ExplanationRequest(BaseModel):
    application_id: str | None = None
    applicant_processor_output: ProcessResponse
    default_model_output: DefaultModelOutput | None = None
    anomaly_model_output: AnomalyModelOutput | None = None
    policy_retrieval_output: PolicyRetrievalOutput | None = None
    orchestrator_output: OrchestratorOutput | None = None


class ExplanationResponse(BaseModel):
    application_id: str | None = None
    recommended_action: str
    summary: str
    model_explanation: list[str]
    anomaly_explanation: list[str]
    policy_explanation: list[str]
    limitations: list[str]
