from app.models.schemas import (
    FeatureVector,
    FieldStatus,
    NormalizedField,
    ProcessResponse,
)
from app.services.ingestion.adapters.base import ParsedApplicantInput
from app.services.ingestion.validator import detect_suspicious_fields


def build_process_response(parsed: ParsedApplicantInput) -> ProcessResponse:
    feature_vector = FeatureVector(
        person_age=parsed.person_age,
        person_income=parsed.person_income,
        person_home_ownership=parsed.person_home_ownership,
        person_emp_length=parsed.person_emp_length,
        loan_intent=parsed.loan_intent,
        loan_grade=parsed.loan_grade,
        loan_amnt=parsed.loan_amnt,
        loan_int_rate=parsed.loan_int_rate,
        loan_percent_income=parsed.loan_percent_income,
        cb_person_default_on_file=parsed.cb_person_default_on_file,
        cb_person_cred_hist_length=parsed.cb_person_cred_hist_length,
    )

    normalized_fields = {
        "person_age": NormalizedField(
            value=parsed.person_age,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["person_age"],
        ),
        "person_income": NormalizedField(
            value=parsed.person_income,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["person_income"],
        ),
        "person_home_ownership": NormalizedField(
            value=parsed.person_home_ownership,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["person_home_ownership"],
        ),
        "person_emp_length": NormalizedField(
            value=parsed.person_emp_length,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["person_emp_length"],
        ),
        "loan_intent": NormalizedField(
            value=parsed.loan_intent,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["loan_intent"],
        ),
        "loan_grade": NormalizedField(
            value=parsed.loan_grade,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["loan_grade"],
        ),
        "loan_amnt": NormalizedField(
            value=parsed.loan_amnt,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["loan_amnt"],
        ),
        "loan_int_rate": NormalizedField(
            value=parsed.loan_int_rate,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["loan_int_rate"],
        ),
        "loan_percent_income": NormalizedField(
            value=parsed.loan_percent_income,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["loan_percent_income"],
        ),
        "cb_person_default_on_file": NormalizedField(
            value=parsed.cb_person_default_on_file,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["cb_person_default_on_file"],
        ),
        "cb_person_cred_hist_length": NormalizedField(
            value=parsed.cb_person_cred_hist_length,
            status=FieldStatus.IDENTIFIED,
            source_text=parsed.source_values["cb_person_cred_hist_length"],
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
