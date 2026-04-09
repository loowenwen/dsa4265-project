from app.models.schemas import ProcessRequest
from app.services.adapters.base import InputAdapter, ParsedApplicantInput
from app.services.normalizer import parse_currency, parse_integer, parse_months, parse_percentage


class FormInputAdapter(InputAdapter):
    def adapt(self, payload: ProcessRequest) -> tuple[ParsedApplicantInput | None, list[dict[str, str]]]:
        errors: list[dict[str, str]] = []

        person_age = self._parse_required(payload.person_age, "person_age", parse_integer, errors)
        person_income = self._parse_required(payload.person_income, "person_income", parse_currency, errors)
        person_home_ownership = self._parse_required_str(payload.person_home_ownership, "person_home_ownership", errors)
        person_emp_length_years = self._parse_required(payload.person_emp_length, "person_emp_length", parse_months, errors)
        loan_intent = self._parse_required_str(payload.loan_intent, "loan_intent", errors)
        loan_grade = self._parse_required_str(payload.loan_grade, "loan_grade", errors)
        loan_amnt = self._parse_required(payload.loan_amnt, "loan_amnt", parse_currency, errors)
        loan_int_rate = self._parse_required(payload.loan_int_rate, "loan_int_rate", parse_percentage, errors)

        loan_percent_income = self._parse_required(payload.loan_percent_income, "loan_percent_income", self._parse_fraction_or_percent, errors)
        cb_person_default_on_file = self._parse_required_str(payload.cb_person_default_on_file, "cb_person_default_on_file", errors)
        cb_person_cred_hist_length = self._parse_required(payload.cb_person_cred_hist_length, "cb_person_cred_hist_length", parse_integer, errors)

        if errors:
            return None, errors

        source_values = {
            "person_age": payload.person_age.strip(),
            "person_income": payload.person_income.strip(),
            "person_home_ownership": payload.person_home_ownership.strip(),
            "person_emp_length": payload.person_emp_length.strip(),
            "loan_intent": payload.loan_intent.strip(),
            "loan_grade": payload.loan_grade.strip(),
            "loan_amnt": payload.loan_amnt.strip(),
            "loan_int_rate": payload.loan_int_rate.strip(),
            "loan_percent_income": payload.loan_percent_income.strip(),
            "cb_person_default_on_file": payload.cb_person_default_on_file.strip(),
            "cb_person_cred_hist_length": payload.cb_person_cred_hist_length.strip(),
            "additional_information": (payload.additional_information or "").strip(),
        }

        parsed = ParsedApplicantInput(
            person_age=float(person_age),
            person_income=float(person_income),
            person_home_ownership=str(person_home_ownership),
            person_emp_length=float(person_emp_length_years) / 12.0 if person_emp_length_years is not None else 0.0,
            loan_intent=str(loan_intent),
            loan_grade=str(loan_grade),
            loan_amnt=float(loan_amnt),
            loan_int_rate=float(loan_int_rate),
            loan_percent_income=float(loan_percent_income),
            cb_person_default_on_file=str(cb_person_default_on_file),
            cb_person_cred_hist_length=float(cb_person_cred_hist_length),
            additional_information=(payload.additional_information or "").strip() or None,
            source_values=source_values,
        )
        return parsed, []

    @staticmethod
    def _parse_required(
        value: str | None,
        field_name: str,
        parser,
        errors: list[dict[str, str]],
    ):
        if value is None or not value.strip():
            errors.append({"field": field_name, "message": "Required field is missing or invalid"})
            return None

        parsed = parser(value)
        if parsed is None:
            errors.append({"field": field_name, "message": "Required field is missing or invalid"})
            return None

        return parsed

    @staticmethod
    def _parse_required_str(
        value: str | None,
        field_name: str,
        errors: list[dict[str, str]],
    ):
        if value is None or not value.strip():
            errors.append({"field": field_name, "message": "Required field is missing or invalid"})
            return None
        return value.strip().upper()

    @staticmethod
    def _parse_fraction_or_percent(value: str | None) -> float | None:
        if value is None or not value.strip():
            return None
        text = value.strip().lower()
        # allow raw fraction like 0.1 or percent like 10%
        from app.services.normalizer import _extract_single_number

        num = _extract_single_number(text)
        if num is None:
            return None
        if "%" in text or "percent" in text or "pct" in text:
            return float(num) / 100.0
        return float(num)
