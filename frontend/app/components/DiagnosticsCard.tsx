import { SuspiciousField } from "../../types/api";

type DiagnosticsCardProps = {
  missingFields: string[];
  suspiciousFields: SuspiciousField[];
  withContainer?: boolean;
  showTitle?: boolean;
};

export default function DiagnosticsCard({
  missingFields,
  suspiciousFields,
  withContainer = true,
  showTitle = true,
}: DiagnosticsCardProps) {
  const content = (
    <>
      {showTitle ? <h2 className="mb-4 text-lg font-semibold text-slate-900">Data Diagnostics</h2> : null}

      <div className="mb-5">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Missing Fields</h3>
        {missingFields.length === 0 ? (
          <p className="text-sm text-slate-700">None</p>
        ) : (
          <ul className="list-disc pl-5 text-sm text-slate-700">
            {missingFields.map((field) => (
              <li key={field}>{field}</li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Suspicious Fields</h3>
        {suspiciousFields.length === 0 ? (
          <p className="text-sm text-slate-700">None</p>
        ) : (
          <ul className="space-y-2 text-sm text-slate-700">
            {suspiciousFields.map((field, index) => (
              <li key={`${field.field}-${index}`} className="rounded border border-slate-200 bg-slate-50 p-2">
                <span className="font-medium text-slate-900">{field.field}</span>: {field.reason} ({field.severity})
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );

  if (!withContainer) {
    return <div>{content}</div>;
  }

  return <section className="surface-card p-6">{content}</section>;
}
