"use client";

import { useState } from "react";

import ApplicantForm from "./components/ApplicantForm";
import DiagnosticsCard from "./components/DiagnosticsCard";
import FeatureVectorCard from "./components/FeatureVectorCard";
import DecisionCard from "./components/DecisionCard";
import { ApiValidationError, processApplicant } from "../lib/api";
import { ProcessResponse } from "../types/api";

type FormValues = {
  annual_income: string;
  loan_amount: string;
  debt_to_income_ratio: string;
  recent_delinquencies: string;
  employment_length_months: string;
  additional_information: string;
};

const INITIAL_VALUES: FormValues = {
  annual_income: "",
  loan_amount: "",
  debt_to_income_ratio: "",
  recent_delinquencies: "",
  employment_length_months: "",
  additional_information: "",
};

const SAMPLE_VALUES: FormValues = {
  annual_income: "$42,000",
  loan_amount: "18000",
  debt_to_income_ratio: "46%",
  recent_delinquencies: "2",
  employment_length_months: "8 months",
  additional_information: "Applicant Summary: no additional demographic details.",
};

const REQUIRED_KEYS: Array<keyof FormValues> = [
  "annual_income",
  "loan_amount",
  "debt_to_income_ratio",
  "recent_delinquencies",
  "employment_length_months",
];

export default function HomePage() {
  const [formValues, setFormValues] = useState<FormValues>(INITIAL_VALUES);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ProcessResponse | null>(null);
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
      setResult(response);
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
              <DecisionCard
                orchestrator={result.orchestrator_output}
                defaultModel={result.default_model_output}
                anomalyModel={result.anomaly_model_output}
                policyOutput={result.policy_retrieval_output}
              />
              <FeatureVectorCard featureVector={result.feature_vector} />
              <DiagnosticsCard
                missingFields={result.missing_fields}
                suspiciousFields={result.suspicious_fields}
              />
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
