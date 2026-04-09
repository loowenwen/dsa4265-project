from app.core.settings import VERY_HIGH_INCOME_THRESHOLD
from app.models.schemas import FeatureVector, SuspiciousField


def detect_suspicious_fields(feature_vector: FeatureVector) -> list[SuspiciousField]:
    suspicious: list[SuspiciousField] = []

    if feature_vector.person_income <= 0:
        suspicious.append(
            SuspiciousField(
                field="person_income",
                reason="Annual income must be greater than zero",
                severity="high",
            )
        )
    elif feature_vector.person_income > VERY_HIGH_INCOME_THRESHOLD:
        suspicious.append(
            SuspiciousField(
                field="person_income",
                reason="Annual income is unusually high",
                severity="medium",
            )
        )

    if feature_vector.loan_amnt <= 0:
        suspicious.append(
            SuspiciousField(
                field="loan_amnt",
                reason="Loan amount must be greater than zero",
                severity="high",
            )
        )

    if feature_vector.loan_percent_income < 0 or feature_vector.loan_percent_income > 1.5:
        suspicious.append(
            SuspiciousField(
                field="loan_percent_income",
                reason="Loan percent income should be a fraction between 0 and 1",
                severity="high",
            )
        )
    elif feature_vector.loan_percent_income > 0.6:
        suspicious.append(
            SuspiciousField(
                field="loan_percent_income",
                reason="Loan percent income above 60%",
                severity="medium",
            )
        )

    if feature_vector.loan_int_rate < 0 or feature_vector.loan_int_rate > 100:
        suspicious.append(
            SuspiciousField(
                field="loan_int_rate",
                reason="Interest rate outside 0-100%",
                severity="high",
            )
        )

    if feature_vector.cb_person_cred_hist_length < 0:
        suspicious.append(
            SuspiciousField(
                field="cb_person_cred_hist_length",
                reason="Credit history length cannot be negative",
                severity="high",
            )
        )

    return suspicious
