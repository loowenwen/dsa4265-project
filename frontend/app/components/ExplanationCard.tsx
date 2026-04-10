import {
  ConsolidatedDecisionPayload,
  ExplanationEvidenceItem,
  ExplanationResponse,
} from "../../types/api";

type ExplanationCardProps = {
  explanation: ExplanationResponse | null;
  decisionPayload: ConsolidatedDecisionPayload | null;
};

const ACTION_STYLES: Record<ExplanationResponse["overall_decision"], string> = {
  accept: "bg-emerald-100 text-emerald-800",
  reject: "bg-red-100 text-red-800",
  manual_review: "bg-amber-100 text-amber-800",
};

const SOURCE_LABELS: Record<ExplanationEvidenceItem["sources"][number], string> = {
  default_risk: "Default Risk",
  anomaly_detection: "Anomaly Detection",
  ai_decision: "AI Decision",
};

function formatDecisionLabel(label: string) {
  return label.replace("_", " ");
}

function EvidenceList({
  items,
  tone,
  title,
}: {
  items: ExplanationEvidenceItem[];
  tone: "green" | "red";
  title: string;
}) {
  if (items.length === 0) {
    return null;
  }

  const toneClasses =
    tone === "green"
      ? "border-emerald-200 bg-emerald-50"
      : "border-rose-200 bg-rose-50";

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      <div className="mt-2 space-y-3">
        {items.map((item, index) => (
          <div key={`${title}-${index}`} className={`rounded border p-3 ${toneClasses}`}>
            <p className="text-sm leading-6 text-slate-800">{item.text}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {item.sources.map((source) => (
                <span
                  key={`${title}-${index}-${source}`}
                  className="rounded-full bg-white/80 px-2 py-1 text-[11px] font-medium text-slate-700"
                >
                  {SOURCE_LABELS[source]}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ExplanationCard({ explanation, decisionPayload }: ExplanationCardProps) {
  if (!explanation || !decisionPayload) {
    return null;
  }

  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Decision</h2>
          <p className="mt-1 text-sm text-slate-600">
            {decisionPayload.overall_decision.decision_note}
          </p>
        </div>
        <span
          className={`rounded px-3 py-1 text-xs font-semibold uppercase ${
            ACTION_STYLES[explanation.overall_decision]
          }`}
        >
          {formatDecisionLabel(explanation.overall_decision)}
        </span>
      </div>

      <div className="mt-4 space-y-5 text-sm text-slate-700">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Summary
          </h3>
          <p className="mt-2 rounded bg-slate-50 p-4 leading-6 text-slate-800">
            {explanation.summary}
          </p>
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Key Metrics
          </h3>
          <div className="mt-2 grid gap-3 sm:grid-cols-2">
            <div className="rounded bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Probability of Default
              </p>
              <p className="mt-1 text-lg font-semibold text-slate-900">
                {explanation.key_metrics.probability_of_default !== null
                  ? explanation.key_metrics.probability_of_default.toFixed(2)
                  : "-"}
              </p>
            </div>
            <div className="rounded bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Anomaly Score
              </p>
              <p className="mt-1 text-lg font-semibold text-slate-900">
                {explanation.key_metrics.anomaly_score !== null
                  ? explanation.key_metrics.anomaly_score.toFixed(2)
                  : "-"}
              </p>
            </div>
          </div>
        </div>

        <EvidenceList items={explanation.supporting_evidence} tone="green" title="Supporting Evidence" />
        <EvidenceList items={explanation.cautionary_evidence} tone="red" title="Cautionary Evidence" />

        {explanation.limitations.length > 0 ? (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Notes
            </h3>
            <ul className="mt-2 space-y-2 text-sm text-slate-600">
              {explanation.limitations.map((item, index) => (
                <li key={`limitation-${index}`} className="rounded bg-slate-50 p-3">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}
