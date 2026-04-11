"use client";

import { FormEvent } from "react";

import { ProcessRequest } from "../../types/api";

type ApplicantFormProps = {
  values: ProcessRequest;
  fieldErrors: Record<string, string>;
  isSubmitting: boolean;
  uploadError: string | null;
  uploadSuccess: string | null;
  onChange: (field: keyof ProcessRequest, value: string) => void;
  onSubmit: () => void;
  onFileUpload: (file: File) => void;
};

const SELECT_OPTIONS: Record<
  "person_home_ownership" | "loan_intent" | "loan_grade" | "cb_person_default_on_file",
  string[]
> = {
  person_home_ownership: ["RENT", "OWN", "MORTGAGE", "OTHER"],
  loan_intent: [
    "EDUCATION",
    "PERSONAL",
    "MEDICAL",
    "VENTURE",
    "HOMEIMPROVEMENT",
    "DEBTCONSOLIDATION",
  ],
  loan_grade: ["A", "B", "C", "D", "E", "F", "G"],
  cb_person_default_on_file: ["N", "Y"],
};

const TEXT_FIELDS: Array<{ name: keyof ProcessRequest; label: string; placeholder: string }> = [
  { name: "person_age", label: "Person Age", placeholder: "35" },
  { name: "person_income", label: "Annual Income", placeholder: "85000" },
  { name: "person_emp_length", label: "Employment Length (years)", placeholder: "6 years" },
  { name: "loan_amnt", label: "Loan Amount", placeholder: "12000" },
  { name: "loan_int_rate", label: "Loan Interest Rate (%)", placeholder: "11.5%" },
  { name: "loan_percent_income", label: "Loan Percent Income", placeholder: "10%" },
  {
    name: "cb_person_cred_hist_length",
    label: "Credit History Length (years)",
    placeholder: "8",
  },
];

const SELECT_LABELS: Record<keyof typeof SELECT_OPTIONS, string> = {
  person_home_ownership: "Home Ownership",
  loan_intent: "Loan Intent",
  loan_grade: "Loan Grade",
  cb_person_default_on_file: "Past Default on Credit File (Y/N)",
};

export default function ApplicantForm({
  values,
  fieldErrors,
  isSubmitting,
  uploadError,
  uploadSuccess,
  onChange,
  onSubmit,
  onFileUpload,
}: ApplicantFormProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form onSubmit={handleSubmit} className="surface-card space-y-8 p-8">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Applicant Intake</h2>
        <p className="mt-2 text-sm text-slate-700">
          Fill the required underwriting fields directly or import one record from CSV, XLSX, or JSON.
        </p>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-slate-50/75 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-600">Upload Record</h3>
            <p className="mt-1 text-sm text-slate-600">
              Accepted formats: <span className="font-semibold text-slate-800">CSV, XLSX, JSON</span>
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800">
            Choose File
            <input
              type="file"
              accept=".csv,.xlsx,.json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  onFileUpload(file);
                }
                event.currentTarget.value = "";
              }}
            />
          </label>
        </div>

        {uploadSuccess ? (
          <p className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {uploadSuccess}
          </p>
        ) : null}
        {uploadError ? (
          <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {uploadError}
          </p>
        ) : null}

      </section>

      <section className="grid gap-6 md:grid-cols-2">
        {TEXT_FIELDS.map((field) => (
          <div key={field.name} className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-900" htmlFor={field.name}>
              {field.label}
            </label>
            <input
              id={field.name}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              placeholder={field.placeholder}
              value={values[field.name]}
              onChange={(event) => onChange(field.name, event.target.value)}
              required
            />
            {fieldErrors[field.name] ? <p className="text-xs text-rose-700">{fieldErrors[field.name]}</p> : null}
          </div>
        ))}

        {(Object.keys(SELECT_OPTIONS) as Array<keyof typeof SELECT_OPTIONS>).map((name) => (
          <div key={name} className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-900" htmlFor={name}>
              {SELECT_LABELS[name]}
            </label>
            <select
              id={name}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              value={values[name]}
              onChange={(event) => onChange(name, event.target.value)}
              required
            >
              <option value="">Select…</option>
              {SELECT_OPTIONS[name].map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            {fieldErrors[name] ? <p className="text-xs text-rose-700">{fieldErrors[name]}</p> : null}
          </div>
        ))}
      </section>

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Processing…" : "Run Applicant Analysis"}
        </button>
      </div>
    </form>
  );
}
