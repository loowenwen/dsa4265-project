import { FeatureVector } from "../../types/api";

type FeatureVectorCardProps = {
  featureVector: FeatureVector;
};

const LABELS: Array<{ key: keyof FeatureVector; label: string }> = [
  { key: "annual_income", label: "Annual Income" },
  { key: "loan_amount", label: "Loan Amount" },
  { key: "debt_to_income_ratio", label: "Debt-to-Income Ratio" },
  { key: "recent_delinquencies", label: "Recent Delinquencies" },
  { key: "employment_length_months", label: "Employment Length (Months)" },
  { key: "demographic_information", label: "Demographic Information" },
];

export default function FeatureVectorCard({ featureVector }: FeatureVectorCardProps) {
  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-lg font-semibold">Feature Vector</h2>
      <div className="space-y-2">
        {LABELS.map((item) => (
          <div key={item.key} className="flex items-start justify-between gap-4 border-b border-slate-100 pb-2">
            <span className="text-sm text-slate-600">{item.label}</span>
            <span className="text-sm font-medium text-slate-900">{String(featureVector[item.key])}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
