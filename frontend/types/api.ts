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
  default_model_output: DefaultModelOutput | null;
  anomaly_model_output: AnomalyModelOutput | null;
  policy_retrieval_output: PolicyRetrievalOutput | null;
  orchestrator_output: OrchestratorOutput | null;
};

export type ValidationDetail = {
  field: string;
  message: string;
};

export type TopFeature = {
  feature: string;
  value: string | number | null;
  direction: "increase_risk" | "decrease_risk" | "unknown";
  importance?: number | null;
  training_percentile?: number | null;
};

export type DefaultModelOutput = {
  model_name?: string | null;
  default_probability: number | null;
  risk_band?: string | null;
  confidence?: number | null;
  in_distribution?: boolean | null;
  top_features: TopFeature[];
};

export type AnomalyReason = {
  feature: string;
  value: string | number | null;
  reason?: string | null;
  expected_range?: string | null;
  severity?: "low" | "medium" | "high" | null;
};

export type AnomalyModelOutput = {
  model_name?: string | null;
  anomaly_score: number | null;
  anomaly_band?: string | null;
  out_of_distribution?: boolean | null;
  top_anomaly_reasons: AnomalyReason[];
};

export type PolicyMatch = {
  rule_id?: string | null;
  title?: string | null;
  snippet: string;
  matched?: boolean;
  match_reason?: string | null;
  severity?: "hard_stop" | "review" | "info" | null;
};

export type PolicyRetrievalOutput = {
  retrieved_rules: PolicyMatch[];
};

export type OrchestratorEvidence = {
  default_probability: number | null;
  anomaly_score: number | null;
  violated_policy_titles: string[] | null;
  missing_required_fields: string[] | null;
  top_features: TopFeature[] | null;
  policy_review_required: boolean | null;
  policy_hard_stop: boolean | null;
};

export type OrchestratorOutput = {
  recommendation: "APPROVE" | "REJECT" | "MANUAL_REVIEW" | null;
  decision_path: string | null;
  reason_codes: string[];
  summary: string | null;
  evidence: OrchestratorEvidence | null;
};
