export type ProcessRequest = {
  person_age: string;
  person_income: string;
  person_home_ownership: string;
  person_emp_length: string;
  loan_intent: string;
  loan_grade: string;
  loan_amnt: string;
  loan_int_rate: string;
  loan_percent_income: string;
  cb_person_default_on_file: string;
  cb_person_cred_hist_length: string;
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
  person_age: number;
  person_income: number;
  person_home_ownership: string;
  person_emp_length: number;
  loan_intent: string;
  loan_grade: string;
  loan_amnt: number;
  loan_int_rate: number;
  loan_percent_income: number;
  cb_person_default_on_file: string;
  cb_person_cred_hist_length: number;
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
  rule_decision: RuleDecision | null;
  ai_decision: AIDecision | null;
  decision_alignment: DecisionAlignment | null;
  policy_support: PolicySupport | null;
  explanation: ExplanationMemo | null;
  decision_payload: ConsolidatedDecisionPayload | null;
};

export type ExplanationRequest = {
  application_id?: string | null;
  decision_payload: ConsolidatedDecisionPayload;
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

export type RuleDecision = {
  decision: "APPROVE" | "REJECT" | "MANUAL_REVIEW";
  reasons: string[];
  triggered_rules: string[];
  missing_info: string[];
  confidence?: number | null;
};

export type AIDecision = {
  decision: "APPROVE" | "REJECT" | "MANUAL_REVIEW";
  confidence?: number | null;
  reasons: string[];
  missing_info: string[];
  policy_considerations: string[];
};

export type DecisionAlignment = {
  status: "AGREE" | "DISAGREE";
  note?: string | null;
};

export type PolicySupport = {
  available: boolean;
  snippets: string[];
};

export type ExplanationMemo = {
  memo: string;
  summary?: string | null;
};

export type ExplanationKeyMetrics = {
  probability_of_default: number | null;
  anomaly_score: number | null;
  risk_band?: string | null;
  anomaly_band?: string | null;
};

export type DecisionLabelFeature = {
  feature: string;
  value: string | number | null;
  contribution?: number | null;
  direction?: "increase_risk" | "decrease_risk" | "unknown";
  reason?: string | null;
};

export type OverallDecisionPayload = {
  decision: "accept" | "reject" | "manual_review";
  decision_source: string;
  decision_note: string;
};

export type DefaultRiskPayload = {
  decision: "accept" | "reject" | "manual_review";
  default_probability: number | null;
  risk_band?: string | null;
  top_features: DecisionLabelFeature[];
};

export type AnomalyDetectionPayload = {
  decision: "accept" | "reject" | "manual_review";
  anomaly_score: number | null;
  anomaly_band?: string | null;
  top_features: DecisionLabelFeature[];
};

export type ConsolidatedAIDecisionPayload = {
  decision: "accept" | "reject" | "manual_review";
  top_reasons: string[];
  raw_input: Record<string, string | number | null>;
};

export type ConsolidatedDecisionPayload = {
  overall_decision: OverallDecisionPayload;
  default_risk: DefaultRiskPayload;
  anomaly_detection: AnomalyDetectionPayload;
  ai_decision: ConsolidatedAIDecisionPayload;
};

export type ExplanationEvidenceItem = {
  text: string;
  sources: Array<"default_risk" | "anomaly_detection" | "ai_decision">;
};

export type ExplanationResponse = {
  application_id?: string | null;
  overall_decision: "accept" | "reject" | "manual_review";
  key_metrics: ExplanationKeyMetrics;
  summary: string;
  supporting_evidence: ExplanationEvidenceItem[];
  cautionary_evidence: ExplanationEvidenceItem[];
  limitations: string[];
};
