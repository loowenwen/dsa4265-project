"use client";

import { FormEvent } from "react";

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

type ApplicantFormProps = {
  values: FormValues;
  fieldErrors: Record<string, string>;
  isSubmitting: boolean;
  onChange: (field: keyof FormValues, value: string) => void;
  onSubmit: () => void;
  onLoadSample: () => void;
};

const SELECT_OPTIONS = {
  person_home_ownership: ["RENT", "OWN", "MORTGAGE", "OTHER"],
  loan_intent: ["EDUCATION", "PERSONAL", "MEDICAL", "VENTURE", "HOMEIMPROVEMENT", "DEBTCONSOLIDATION"],
  loan_grade: ["A", "B", "C", "D", "E", "F", "G"],
  cb_person_default_on_file: ["N", "Y"],
};

const TEXT_FIELDS: Array<{ name: keyof FormValues; label: string; placeholder: string; type?: string }> = [
  { name: "person_age", label: "Person Age", placeholder: "35" },
  { name: "person_income", label: "Annual Income", placeholder: "85000" },
  { name: "person_emp_length", label: "Employment Length (years)", placeholder: "6 years" },
  { name: "loan_amnt", label: "Loan Amount", placeholder: "12000" },
  { name: "loan_int_rate", label: "Loan Interest Rate (%)", placeholder: "11.5%" },
  { name: "loan_percent_income", label: "Loan Percent Income", placeholder: "10%" },
  { name: "cb_person_cred_hist_length", label: "Credit History Length (years)", placeholder: "8" },
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
  onChange,
  onSubmit,
  onLoadSample,
}: ApplicantFormProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg bg-white p-6 shadow">
      <h2 className="text-lg font-semibold">Applicant Form</h2>

      {TEXT_FIELDS.map((field) => (
        <div key={field.name} className="space-y-1">
          <label className="block text-sm font-medium text-slate-700" htmlFor={field.name}>
            {field.label} <span className="text-red-600">*</span>
          </label>
          <input
            id={field.name}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            placeholder={field.placeholder}
            value={values[field.name]}
            onChange={(event) => onChange(field.name, event.target.value)}
            required
          />
          {fieldErrors[field.name] ? (
            <p className="text-sm text-red-600">{fieldErrors[field.name]}</p>
          ) : null}
        </div>
      ))}

      {(["person_home_ownership", "loan_intent", "loan_grade", "cb_person_default_on_file"] as Array<
        keyof typeof SELECT_OPTIONS
      >).map((name) => (
        <div key={name} className="space-y-1">
          <label className="block text-sm font-medium text-slate-700" htmlFor={name}>
            {SELECT_LABELS[name]} <span className="text-red-600">*</span>
          </label>
          <select
            id={name}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            value={values[name] as string}
            onChange={(event) => onChange(name as keyof FormValues, event.target.value)}
            required
          >
            <option value="">Select...</option>
            {SELECT_OPTIONS[name].map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          {fieldErrors[name] ? <p className="text-sm text-red-600">{fieldErrors[name]}</p> : null}
        </div>
      ))}

      <div className="space-y-1">
        <label className="block text-sm font-medium text-slate-700" htmlFor="additional_information">
          Additional Information (Optional)
        </label>
        <textarea
          id="additional_information"
          className="min-h-28 w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          placeholder="Add any extra context..."
          value={values.additional_information}
          onChange={(event) => onChange("additional_information", event.target.value)}
        />
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Processing..." : "Process Applicant"}
        </button>
        <button
          type="button"
          onClick={onLoadSample}
          className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
        >
          Load Sample
        </button>
      </div>
    </form>
  );
}
