"use client";

import { FormEvent } from "react";

type FormValues = {
  annual_income: string;
  loan_amount: string;
  debt_to_income_ratio: string;
  recent_delinquencies: string;
  employment_length_months: string;
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

const REQUIRED_FIELDS: Array<{ name: keyof FormValues; label: string; placeholder: string }> = [
  { name: "annual_income", label: "Annual Income", placeholder: "$42,000" },
  { name: "loan_amount", label: "Loan Amount", placeholder: "18000" },
  { name: "debt_to_income_ratio", label: "Debt-to-Income Ratio", placeholder: "46%" },
  { name: "recent_delinquencies", label: "Recent Delinquencies", placeholder: "2" },
  { name: "employment_length_months", label: "Employment Length", placeholder: "8 months" },
];

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

      {REQUIRED_FIELDS.map((field) => (
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
