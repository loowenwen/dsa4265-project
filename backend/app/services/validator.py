from app.core.settings import (
    DTI_MEDIUM_THRESHOLD,
    LOAN_TO_INCOME_MULTIPLIER_ALERT,
    VERY_HIGH_INCOME_THRESHOLD,
)
from app.models.schemas import FeatureVector, SuspiciousField


def detect_suspicious_fields(feature_vector: FeatureVector) -> list[SuspiciousField]:
    suspicious: list[SuspiciousField] = []

    if feature_vector.annual_income <= 0:
        suspicious.append(
            SuspiciousField(
                field="annual_income",
                reason="Annual income must be greater than zero",
                severity="high",
            )
        )
    elif feature_vector.annual_income > VERY_HIGH_INCOME_THRESHOLD:
        suspicious.append(
            SuspiciousField(
                field="annual_income",
                reason="Annual income is unusually high",
                severity="medium",
            )
        )

    if feature_vector.loan_amount <= 0:
        suspicious.append(
            SuspiciousField(
                field="loan_amount",
                reason="Loan amount must be greater than zero",
                severity="high",
            )
        )
    elif feature_vector.loan_amount > feature_vector.annual_income * LOAN_TO_INCOME_MULTIPLIER_ALERT:
        suspicious.append(
            SuspiciousField(
                field="loan_amount",
                reason="Loan amount is high relative to annual income",
                severity="high",
            )
        )

    if feature_vector.debt_to_income_ratio < 0 or feature_vector.debt_to_income_ratio > 100:
        suspicious.append(
            SuspiciousField(
                field="debt_to_income_ratio",
                reason="Debt-to-income ratio is outside 0-100 range",
                severity="high",
            )
        )
    elif feature_vector.debt_to_income_ratio > DTI_MEDIUM_THRESHOLD:
        suspicious.append(
            SuspiciousField(
                field="debt_to_income_ratio",
                reason="DTI above 43%",
                severity="medium",
            )
        )

    if feature_vector.recent_delinquencies < 0:
        suspicious.append(
            SuspiciousField(
                field="recent_delinquencies",
                reason="Recent delinquencies cannot be negative",
                severity="high",
            )
        )

    if feature_vector.employment_length_months < 0:
        suspicious.append(
            SuspiciousField(
                field="employment_length_months",
                reason="Employment length cannot be negative",
                severity="high",
            )
        )

    return suspicious
