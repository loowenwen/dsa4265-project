import { FeatureVector } from "../../types/api";

type FeatureVectorCardProps = {
  featureVector: FeatureVector;
};

const LABELS: Array<{ key: keyof FeatureVector; label: string }> = [
  { key: "person_age", label: "Person Age" },
  { key: "person_income", label: "Person Income" },
  { key: "person_home_ownership", label: "Home Ownership" },
  { key: "person_emp_length", label: "Employment Length (years)" },
  { key: "loan_intent", label: "Loan Intent" },
  { key: "loan_grade", label: "Loan Grade" },
  { key: "loan_amnt", label: "Loan Amount" },
  { key: "loan_int_rate", label: "Interest Rate" },
  { key: "loan_percent_income", label: "Loan Percent Income" },
  { key: "cb_person_default_on_file", label: "Default On File" },
  { key: "cb_person_cred_hist_length", label: "Credit History Length (years)" },
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
