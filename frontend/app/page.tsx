"use client";

import { useState } from "react";

import ApplicantForm from "./components/ApplicantForm";
import DiagnosticsCard from "./components/DiagnosticsCard";
import FeatureVectorCard from "./components/FeatureVectorCard";
import ExplanationCard from "./components/ExplanationCard";
import DecisionCard from "./components/DecisionCard";
import { ApiValidationError, explainApplication, processApplicant } from "../lib/api";
import { ExplanationResponse, ProcessResponse } from "../types/api";

type FormValues = {
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
  additional_information: string;
};

const INITIAL_VALUES: FormValues = {
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
  additional_information: "",
};

const SAMPLE_VALUES: FormValues = {
  person_age: "35",
  person_income: "85000",
  person_home_ownership: "RENT",
  person_emp_length: "6 years",
  loan_intent: "EDUCATION",
  loan_grade: "C",
  loan_amnt: "12000",
  loan_int_rate: "11.5%",
  loan_percent_income: "10%",
  cb_person_default_on_file: "N",
  cb_person_cred_hist_length: "8",
  additional_information: "",
};

const REQUIRED_KEYS: Array<keyof FormValues> = [
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

export default function HomePage() {
  const [formValues, setFormValues] = useState<FormValues>(INITIAL_VALUES);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const handleChange = (field: keyof FormValues, value: string) => {
    setFormValues((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => {
      if (!prev[field]) {
        return prev;
      }

      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const handleSubmit = async () => {
    setGlobalError(null);
    setResult(null);
    setExplanation(null);

    const clientErrors: Record<string, string> = {};
    for (const key of REQUIRED_KEYS) {
      if (!formValues[key].trim()) {
        clientErrors[key] = "This field is required.";
      }
    }

    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setFieldErrors({});
    setIsSubmitting(true);

    try {
      const response = await processApplicant(formValues);
      const explanationResponse = await explainApplication({
        applicant_processor_output: response,
        default_model_output: response.default_model_output,
        anomaly_model_output: response.anomaly_model_output,
        policy_retrieval_output: response.policy_retrieval_output,
        orchestrator_output: response.orchestrator_output,
      });
      setResult(response);
      setExplanation(explanationResponse);
    } catch (error) {
      if (error instanceof ApiValidationError) {
        const nextFieldErrors: Record<string, string> = {};
        for (const detail of error.details) {
          if (detail.field) {
            nextFieldErrors[detail.field] = detail.message;
          }
        }
        setFieldErrors(nextFieldErrors);
      } else {
        setGlobalError("Unable to process request. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLoadSample = () => {
    setFormValues(SAMPLE_VALUES);
    setFieldErrors({});
    setGlobalError(null);
  };

  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="mb-2 text-3xl font-bold text-slate-900">Applicant Information Processor</h1>
      <p className="mb-6 text-sm text-slate-600">
        Enter required applicant fields, then normalize into a structured feature vector.
      </p>

      {globalError ? <div className="mb-4 rounded bg-red-100 px-4 py-2 text-sm text-red-800">{globalError}</div> : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <ApplicantForm
          values={formValues}
          fieldErrors={fieldErrors}
          isSubmitting={isSubmitting}
          onChange={handleChange}
          onSubmit={handleSubmit}
          onLoadSample={handleLoadSample}
        />

        <div className="space-y-6">
          {result ? (
            <>
              <ExplanationCard
                explanation={explanation}
                ruleDecision={result.rule_decision}
                aiDecision={result.ai_decision}
                alignment={result.decision_alignment}
              />
              <DecisionCard
                ruleDecision={result.rule_decision}
                aiDecision={result.ai_decision}
                alignment={result.decision_alignment}
                defaultModel={result.default_model_output}
                anomalyModel={result.anomaly_model_output}
                policyOutput={result.policy_retrieval_output}
              />
              <FeatureVectorCard featureVector={result.feature_vector} />
              <DiagnosticsCard missingFields={result.missing_fields} suspiciousFields={result.suspicious_fields} />
            </>
          ) : (
            <section className="rounded-lg bg-white p-6 text-sm text-slate-600 shadow">
              Submit the form to see normalized output and diagnostics.
            </section>
          )}
        </div>
      </div>
    </main>
  );
}
