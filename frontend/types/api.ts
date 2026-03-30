export type ProcessRequest = {
  annual_income: string;
  loan_amount: string;
  debt_to_income_ratio: string;
  recent_delinquencies: string;
  employment_length_months: string;
  additional_information?: string;
};

export type FieldStatus = "identified" | "cannot_identify";

export type NormalizedField = {
  value: string | number;
  status: FieldStatus;
  source_text: string | null;
};

export type SuspiciousField = {
  field: string;
  reason: string;
  severity: "low" | "medium" | "high";
};

export type FeatureVector = {
  annual_income: number;
  loan_amount: number;
  debt_to_income_ratio: number;
  recent_delinquencies: number;
  employment_length_months: number;
  demographic_information: string;
};

export type ProcessResponse = {
  feature_vector: FeatureVector;
  normalized_fields: Record<string, NormalizedField>;
  missing_fields: string[];
  suspicious_fields: SuspiciousField[];
};

export type ValidationDetail = {
  field: string;
  message: string;
};
