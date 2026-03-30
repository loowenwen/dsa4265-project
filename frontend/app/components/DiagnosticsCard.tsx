import { SuspiciousField } from "../../types/api";

type DiagnosticsCardProps = {
  missingFields: string[];
  suspiciousFields: SuspiciousField[];
};

export default function DiagnosticsCard({
  missingFields,
  suspiciousFields,
}: DiagnosticsCardProps) {
  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-lg font-semibold">Diagnostics</h2>

      <div className="mb-5">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Missing Fields</h3>
        {missingFields.length === 0 ? (
          <p className="text-sm text-slate-600">None</p>
        ) : (
          <ul className="list-disc pl-5 text-sm text-slate-700">
            {missingFields.map((field) => (
              <li key={field}>{field}</li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Suspicious Fields
        </h3>
        {suspiciousFields.length === 0 ? (
          <p className="text-sm text-slate-600">None</p>
        ) : (
          <ul className="space-y-2 text-sm text-slate-700">
            {suspiciousFields.map((field, index) => (
              <li key={`${field.field}-${index}`} className="rounded bg-amber-50 p-2">
                <span className="font-medium">{field.field}</span>: {field.reason} ({field.severity})
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
