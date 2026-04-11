import { ProcessRequest } from "../types/api";

export type ScenarioKey = "accept" | "manual_review" | "reject";

export const REQUIRED_FIELDS: Array<keyof ProcessRequest> = [
  "person_age",
  "person_income",
  "person_home_ownership",
  "person_emp_length",
  "loan_intent",
  "loan_grade",
  "loan_amnt",
  "loan_int_rate",
  "loan_percent_income",
  "cb_person_default_on_file",
  "cb_person_cred_hist_length",
];

export const EMPTY_FORM_VALUES: ProcessRequest = {
  person_age: "",
  person_income: "",
  person_home_ownership: "",
  person_emp_length: "",
  loan_intent: "",
  loan_grade: "",
  loan_amnt: "",
  loan_int_rate: "",
  loan_percent_income: "",
  cb_person_default_on_file: "",
  cb_person_cred_hist_length: "",
};

export const SAMPLE_SCENARIOS: Record<ScenarioKey, ProcessRequest> = {
  accept: {
    person_age: "36",
    person_income: "120000",
    person_home_ownership: "MORTGAGE",
    person_emp_length: "9 years",
    loan_intent: "HOMEIMPROVEMENT",
    loan_grade: "A",
    loan_amnt: "9000",
    loan_int_rate: "7.2%",
    loan_percent_income: "7%",
    cb_person_default_on_file: "N",
    cb_person_cred_hist_length: "12",
  },
  manual_review: {
    person_age: "29",
    person_income: "42000",
    person_home_ownership: "RENT",
    person_emp_length: "1 year",
    loan_intent: "PERSONAL",
    loan_grade: "D",
    loan_amnt: "18000",
    loan_int_rate: "15.5%",
    loan_percent_income: "46%",
    cb_person_default_on_file: "N",
    cb_person_cred_hist_length: "4",
  },
  reject: {
    person_age: "22",
    person_income: "25000",
    person_home_ownership: "RENT",
    person_emp_length: "4 months",
    loan_intent: "PERSONAL",
    loan_grade: "G",
    loan_amnt: "30000",
    loan_int_rate: "21%",
    loan_percent_income: "95%",
    cb_person_default_on_file: "Y",
    cb_person_cred_hist_length: "1",
  },
};

export const SAMPLE_FILES: Record<ScenarioKey, string> = {
  accept: "/samples/accept_application.json",
  manual_review: "/samples/manual_review_application.csv",
  reject: "/samples/reject_application.xlsx",
};
