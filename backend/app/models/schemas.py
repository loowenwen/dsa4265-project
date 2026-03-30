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
