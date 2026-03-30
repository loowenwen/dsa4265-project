from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.schemas import ProcessRequest


@dataclass
class ParsedApplicantInput:
    annual_income: float
    loan_amount: float
    debt_to_income_ratio: float
    recent_delinquencies: int
    employment_length_months: int
    additional_information: str | None
    source_values: dict[str, str]


class InputAdapter(ABC):
    @abstractmethod
    def adapt(self, payload: ProcessRequest) -> tuple[ParsedApplicantInput | None, list[dict[str, str]]]:
        raise NotImplementedError
