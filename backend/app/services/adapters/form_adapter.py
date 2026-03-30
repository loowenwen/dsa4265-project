from app.models.schemas import ProcessRequest
from app.services.adapters.base import InputAdapter, ParsedApplicantInput
from app.services.normalizer import parse_currency, parse_integer, parse_months, parse_percentage


class FormInputAdapter(InputAdapter):
    def adapt(self, payload: ProcessRequest) -> tuple[ParsedApplicantInput | None, list[dict[str, str]]]:
        errors: list[dict[str, str]] = []

        annual_income = self._parse_required(payload.annual_income, "annual_income", parse_currency, errors)
        loan_amount = self._parse_required(payload.loan_amount, "loan_amount", parse_currency, errors)
        debt_to_income_ratio = self._parse_required(
            payload.debt_to_income_ratio,
            "debt_to_income_ratio",
            parse_percentage,
            errors,
        )
        recent_delinquencies = self._parse_required(
            payload.recent_delinquencies,
            "recent_delinquencies",
            parse_integer,
            errors,
        )
        employment_length_months = self._parse_required(
            payload.employment_length_months,
            "employment_length_months",
            parse_months,
            errors,
        )

        if errors:
            return None, errors

        source_values = {
            "annual_income": payload.annual_income.strip(),
            "loan_amount": payload.loan_amount.strip(),
            "debt_to_income_ratio": payload.debt_to_income_ratio.strip(),
            "recent_delinquencies": payload.recent_delinquencies.strip(),
            "employment_length_months": payload.employment_length_months.strip(),
            "additional_information": (payload.additional_information or "").strip(),
        }

        parsed = ParsedApplicantInput(
            annual_income=float(annual_income),
            loan_amount=float(loan_amount),
            debt_to_income_ratio=float(debt_to_income_ratio),
            recent_delinquencies=int(recent_delinquencies),
            employment_length_months=int(employment_length_months),
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
