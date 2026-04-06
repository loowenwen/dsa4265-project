import { AnomalyModelOutput, DefaultModelOutput, OrchestratorOutput, PolicyRetrievalOutput } from "../../types/api";

interface DecisionCardProps {
  orchestrator: OrchestratorOutput | null;
  defaultModel: DefaultModelOutput | null;
  anomalyModel: AnomalyModelOutput | null;
  policyOutput: PolicyRetrievalOutput | null;
}

export default function DecisionCard({ orchestrator, defaultModel, anomalyModel, policyOutput }: DecisionCardProps) {
  if (!orchestrator) {
    return null;
  }

  const recommendation = orchestrator.recommendation ?? "MANUAL_REVIEW";
  const defaultProb = orchestrator.evidence?.default_probability ?? defaultModel?.default_probability ?? null;
  const anomalyScore = orchestrator.evidence?.anomaly_score ?? anomalyModel?.anomaly_score ?? null;
  const reasonCodes = orchestrator.reason_codes ?? [];
  const policyRules = policyOutput?.retrieved_rules ?? [];

  const badgeColor = recommendation === "APPROVE" ? "bg-emerald-100 text-emerald-800" : recommendation === "REJECT" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800";

  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Decision</h2>
        <span className={`rounded px-3 py-1 text-xs font-semibold uppercase ${badgeColor}`}>
          {recommendation.replace("_", " ")}
        </span>
      </div>

      <div className="mt-4 grid gap-3 text-sm text-slate-700">
        <div className="flex justify-between">
          <span className="text-slate-500">Default Probability</span>
          <span className="font-medium">{defaultProb !== null ? defaultProb.toFixed(2) : "-"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Anomaly Score</span>
          <span className="font-medium">{anomalyScore !== null ? anomalyScore.toFixed(2) : "-"}</span>
        </div>
        {orchestrator.summary ? (
          <p className="rounded bg-slate-50 p-3 text-slate-700">{orchestrator.summary}</p>
        ) : null}

        {reasonCodes.length > 0 ? (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Reason Codes</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {reasonCodes.map((code) => (
                <span key={code} className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-800">
                  {code}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {policyRules.length > 0 ? (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Policy Triggers</h3>
            <ul className="mt-2 space-y-2">
              {policyRules.map((rule, idx) => (
                <li key={`${rule.rule_id || idx}`} className="rounded border border-slate-200 p-2">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>{rule.title || "Policy"}</span>
                    {rule.severity ? <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] uppercase">{rule.severity}</span> : null}
                  </div>
                  <p className="text-sm text-slate-700">{rule.snippet}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}
