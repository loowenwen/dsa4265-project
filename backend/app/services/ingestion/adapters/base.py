from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.schemas import ProcessRequest


@dataclass
class ParsedApplicantInput:
    person_age: float
    person_income: float
    person_home_ownership: str
    person_emp_length: float  # years
    loan_intent: str
    loan_grade: str
    loan_amnt: float
    loan_int_rate: float
    loan_percent_income: float
    cb_person_default_on_file: str
    cb_person_cred_hist_length: float
    additional_information: str | None
    source_values: dict[str, str]


class InputAdapter(ABC):
    @abstractmethod
    def adapt(self, payload: ProcessRequest) -> tuple[ParsedApplicantInput | None, list[dict[str, str]]]:
        raise NotImplementedError
