import {
  AIDecision,
  AnomalyModelOutput,
  DefaultModelOutput,
  DecisionAlignment,
  PolicyRetrievalOutput,
  RuleDecision,
} from "../../types/api";

interface DecisionCardProps {
  ruleDecision: RuleDecision | null;
  aiDecision: AIDecision | null;
  alignment: DecisionAlignment | null;
  defaultModel: DefaultModelOutput | null;
  anomalyModel: AnomalyModelOutput | null;
  policyOutput: PolicyRetrievalOutput | null;
}

function badge(decision?: string | null) {
  if (decision === "APPROVE") return "bg-emerald-100 text-emerald-800";
  if (decision === "REJECT") return "bg-red-100 text-red-800";
  return "bg-amber-100 text-amber-800";
}

export default function DecisionCard({
  ruleDecision,
  aiDecision,
  alignment,
  defaultModel,
  anomalyModel,
  policyOutput,
}: DecisionCardProps) {
  if (!ruleDecision && !aiDecision) return null;

  const defaultProb = defaultModel?.default_probability ?? null;
  const anomalyScore = anomalyModel?.anomaly_score ?? null;
  const policyRules = policyOutput?.retrieved_rules ?? [];

  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Decisions</h2>
        {alignment ? (
          <span
            className={`rounded px-3 py-1 text-xs font-semibold uppercase ${
              alignment.status === "AGREE" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
            }`}
          >
            {alignment.status}
          </span>
        ) : null}
      </div>

      <div className="mt-4 grid gap-4 text-sm text-slate-700">
        <div className="grid gap-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Rule Decision</span>
            <span className={`rounded px-2 py-1 text-xs font-semibold uppercase ${badge(ruleDecision?.decision)}`}>
              {ruleDecision?.decision ?? "N/A"}
            </span>
          </div>
          {ruleDecision?.reasons?.length ? (
            <ul className="list-disc pl-5 text-slate-700">
              {ruleDecision.reasons.map((r, idx) => (
                <li key={`r-${idx}`}>{r}</li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className="grid gap-2 border-t border-slate-100 pt-3">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">AI Decision</span>
            <span className={`rounded px-2 py-1 text-xs font-semibold uppercase ${badge(aiDecision?.decision)}`}>
              {aiDecision?.decision ?? "N/A"}
            </span>
          </div>
          {aiDecision?.reasons?.length ? (
            <ul className="list-disc pl-5 text-slate-700">
              {aiDecision.reasons.map((r, idx) => (
                <li key={`ai-${idx}`}>{r}</li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className="grid gap-1 border-t border-slate-100 pt-3">
          <div className="flex justify-between">
            <span className="text-slate-500">Default Probability</span>
            <span className="font-medium">{defaultProb !== null ? defaultProb.toFixed(2) : "-"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Anomaly Score</span>
            <span className="font-medium">{anomalyScore !== null ? anomalyScore.toFixed(2) : "-"}</span>
          </div>
        </div>

        {policyRules.length > 0 ? (
          <div className="border-t border-slate-100 pt-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Policy Snippets</h3>
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
