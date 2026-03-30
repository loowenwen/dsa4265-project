from app.models.schemas import (
    FeatureVector,
    FieldStatus,
    NormalizedField,
    ProcessResponse,
)
from app.services.adapters.base import ParsedApplicantInput
from app.services.enricher import extract_demographic_information
from app.services.validator import detect_suspicious_fields


def build_process_response(parsed: ParsedApplicantInput) -> ProcessResponse:
    demographic_value, demographic_source = extract_demographic_information(parsed.additional_information)

    feature_vector = FeatureVector(
        annual_income=parsed.annual_income,
        loan_amount=parsed.loan_amount,
        debt_to_income_ratio=parsed.debt_to_income_ratio,
        recent_delinquencies=parsed.recent_delinquencies,
        employment_length_months=parsed.employment_length_months,
        demographic_information=demographic_value,
    )

    normalized_fields = {
        "annual_income": NormalizedField(
            value=parsed.annual_income,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["annual_income"],
        ),
        "loan_amount": NormalizedField(
            value=parsed.loan_amount,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["loan_amount"],
        ),
        "debt_to_income_ratio": NormalizedField(
            value=parsed.debt_to_income_ratio,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["debt_to_income_ratio"],
        ),
        "recent_delinquencies": NormalizedField(
            value=parsed.recent_delinquencies,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["recent_delinquencies"],
        ),
        "employment_length_months": NormalizedField(
            value=parsed.employment_length_months,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["employment_length_months"],
        ),
        "demographic_information": NormalizedField(
            value=demographic_value,
            status=(
                FieldStatus.CANNOT_IDENTIFY
                if demographic_value == "cannot identify"
                else FieldStatus.IDENTIFIED
            ),
            source_text=demographic_source,
        ),
    }

    missing_fields = [
        field_name
        for field_name, normalized_field in normalized_fields.items()
        if normalized_field.status == FieldStatus.CANNOT_IDENTIFY
    ]

    suspicious_fields = detect_suspicious_fields(feature_vector)

    return ProcessResponse(
        feature_vector=feature_vector,
        normalized_fields=normalized_fields,
        missing_fields=missing_fields,
        suspicious_fields=suspicious_fields,
    )
