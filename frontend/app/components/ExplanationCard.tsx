import { AIDecision, DecisionAlignment, ExplanationResponse, RuleDecision } from "../../types/api";

type ExplanationCardProps = {
  explanation: ExplanationResponse | null;
  ruleDecision: RuleDecision | null;
  aiDecision: AIDecision | null;
  alignment: DecisionAlignment | null;
};

const ACTION_STYLES: Record<string, string> = {
  APPROVE: "bg-emerald-100 text-emerald-800",
  REJECT: "bg-red-100 text-red-800",
  MANUAL_REVIEW: "bg-amber-100 text-amber-800",
};

export default function ExplanationCard({ explanation, ruleDecision, aiDecision, alignment }: ExplanationCardProps) {
  if (!explanation) {
    return null;
  }

  const probability = explanation.key_metrics.probability_of_default;
  const anomalyScore = explanation.key_metrics.anomaly_score;

  // Determine final decision summary
  const finalDecision =
    alignment && alignment.status === "AGREE"
      ? ruleDecision?.decision || aiDecision?.decision || "MANUAL_REVIEW"
      : ruleDecision?.decision || "MANUAL_REVIEW";

  const alignmentNote =
    alignment && alignment.status === "DISAGREE"
      ? alignment.note || "Rule and AI decisions differ; escalate."
      : null;

  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Explanation</h2>
          {alignmentNote ? <p className="text-xs text-amber-700 mt-1">{alignmentNote}</p> : null}
        </div>
        {finalDecision ? (
          <span className={`rounded px-3 py-1 text-xs font-semibold uppercase ${ACTION_STYLES[finalDecision] || "bg-slate-100 text-slate-700"}`}>
            {finalDecision}
          </span>
        ) : null}
      </div>

      <div className="mt-2 space-y-4 text-sm text-slate-700">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Explanation
          </h3>
          <p className="mt-2 rounded bg-slate-50 p-4 leading-6 text-slate-800">
            {explanation.reasons}
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
                {probability !== null ? probability.toFixed(2) : "-"}
              </p>
            </div>
            <div className="rounded bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Anomaly Score
              </p>
              <p className="mt-1 text-lg font-semibold text-slate-900">
                {anomalyScore !== null ? anomalyScore.toFixed(2) : "-"}
              </p>
            </div>
          </div>
        </div>

        {explanation.reason_codes.length > 0 ? (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Reason Codes
            </h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {explanation.reason_codes.map((code) => (
                <span
                  key={code}
                  className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-800"
                >
                  {code}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {explanation.policy_references.length > 0 ? (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Policy References
            </h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {explanation.policy_references.map((item) => (
                <span
                  key={item}
                  className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-800"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
