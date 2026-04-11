"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import ApplicantForm from "../components/ApplicantForm";
import ProcessingBar from "../components/ProcessingBar";
import { ApiValidationError, explainApplication, processApplicant } from "../../lib/api";
import { FileParseError, parseApplicantFile } from "../../lib/applicantFileParser";
import { EMPTY_FORM_VALUES, REQUIRED_FIELDS } from "../../lib/applicantForm";
import { saveResultBundle } from "../../lib/resultStore";
import { ProcessRequest } from "../../types/api";

const PROCESS_STEPS = {
  validating: { progress: 18, label: "Validating required fields" },
  normalizing: { progress: 45, label: "Normalizing applicant profile" },
  scoring: { progress: 68, label: "Running risk and anomaly models" },
  explaining: { progress: 86, label: "Generating grounded explanation" },
  finalizing: { progress: 100, label: "Preparing your decision report" },
} as const;

export default function ApplyPage() {
  const router = useRouter();

  const [formValues, setFormValues] = useState<ProcessRequest>(EMPTY_FORM_VALUES);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState<string>(PROCESS_STEPS.validating.label);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const tickerRef = useRef<number | null>(null);

  const stopTicker = () => {
    if (tickerRef.current !== null) {
      window.clearInterval(tickerRef.current);
      tickerRef.current = null;
    }
  };

  const startTicker = () => {
    stopTicker();
    tickerRef.current = window.setInterval(() => {
      setProgress((current) => {
        if (current >= 92) {
          return current;
        }
        const next = current + Math.random() * 5 + 1;
        return Math.min(92, next);
      });
    }, 350);
  };

  const advanceProgress = (next: number) => {
    setProgress((current) => Math.max(current, next));
  };

  const setStep = (step: keyof typeof PROCESS_STEPS) => {
    advanceProgress(PROCESS_STEPS[step].progress);
    setProgressLabel(PROCESS_STEPS[step].label);
  };

  const handleChange = (field: keyof ProcessRequest, value: string) => {
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

  const handleFileUpload = async (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);
    setGlobalError(null);

    try {
      const parsed = await parseApplicantFile(file);
      setFormValues(parsed);
      setFieldErrors({});
      setUploadSuccess(`Loaded ${file.name}. You can review and submit.`);
    } catch (error) {
      if (error instanceof FileParseError) {
        setUploadError(error.message);
      } else {
        setUploadError("Unable to parse uploaded file.");
      }
    }
  };

  const handleSubmit = async () => {
    setGlobalError(null);
    setProgress(0);

    const clientErrors: Record<string, string> = {};
    for (const key of REQUIRED_FIELDS) {
      if (!formValues[key].trim()) {
        clientErrors[key] = "This field is required.";
      }
    }

    setStep("validating");
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setFieldErrors({});
    setIsSubmitting(true);
    advanceProgress(8);
    setProgressLabel("Starting analysis");
    startTicker();

    try {
      setStep("normalizing");
      const processResponse = await processApplicant(formValues);

      if (!processResponse.decision_payload) {
        throw new Error("Decision payload unavailable from backend.");
      }

      setStep("scoring");
      const explanationResponse = await explainApplication({
        decision_payload: processResponse.decision_payload,
      });

      setStep("explaining");
      saveResultBundle({
        submittedAt: new Date().toISOString(),
        process: processResponse,
        explanation: explanationResponse,
      });

      setStep("finalizing");
      stopTicker();
      window.setTimeout(() => {
        router.push("/result");
      }, 280);
    } catch (error) {
      stopTicker();

      if (error instanceof ApiValidationError) {
        const nextFieldErrors: Record<string, string> = {};
        for (const detail of error.details) {
          if (detail.field) {
            nextFieldErrors[detail.field] = detail.message;
          }
        }
        setFieldErrors(nextFieldErrors);
      } else {
        setGlobalError("Unable to process this application right now. Please retry.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="mx-auto max-w-7xl px-6 pb-12 pt-8 md:px-10">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Applicant Information Processor
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900 md:text-4xl">Underwriting Intake</h1>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <ApplicantForm
          values={formValues}
          fieldErrors={fieldErrors}
          isSubmitting={isSubmitting}
          uploadError={uploadError}
          uploadSuccess={uploadSuccess}
          onChange={handleChange}
          onSubmit={handleSubmit}
          onFileUpload={handleFileUpload}
        />

        <div className="space-y-6">
          <ProcessingBar active={isSubmitting} progress={progress} stageLabel={progressLabel} />

          <section className="surface-card p-7">
            <h2 className="text-xl font-semibold text-slate-900">What Happens Next</h2>
            <ol className="mt-4 space-y-3 text-sm text-slate-700">
              <li>1. Input is normalized and validated.</li>
              <li>2. Default-risk and anomaly models score the profile.</li>
              <li>3. Rule engine + AI decision are consolidated.</li>
              <li>4. A grounded explanation is produced for review.</li>
            </ol>
          </section>

          {globalError ? (
            <section className="rounded-2xl border border-rose-300 bg-rose-50 px-5 py-4 text-sm text-rose-800">
              {globalError}
            </section>
          ) : null}
        </div>
      </div>
    </main>
  );
}
