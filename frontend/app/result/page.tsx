"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import CollapsibleSection from "../components/CollapsibleSection";
import DecisionCard from "../components/DecisionCard";
import DiagnosticsCard from "../components/DiagnosticsCard";
import ExplanationCard from "../components/ExplanationCard";
import { clearResultBundle, loadResultBundle } from "../../lib/resultStore";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return date.toLocaleString();
}

export default function ResultPage() {
  const [bundle, setBundle] = useState<ReturnType<typeof loadResultBundle> | undefined>(undefined);

  useEffect(() => {
    setBundle(loadResultBundle());
  }, []);

  if (bundle === undefined) {
    return (
      <main className="mx-auto max-w-7xl px-6 pb-12 pt-8 md:px-10">
        <section className="surface-card p-8 text-sm text-slate-600">Loading latest result...</section>
      </main>
    );
  }

  if (!bundle) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14 md:px-10">
        <section className="surface-card p-10 text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">No Active Result</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">Start a New Evaluation</h1>
          <p className="mt-3 text-sm text-slate-700">
            Submit an application first, then return here to review decisions and explanation.
          </p>
          <div className="mt-7">
            <Link href="/apply" className="rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white">
              Go to Input Page
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const { process, explanation, submittedAt } = bundle;

  return (
    <main className="mx-auto max-w-7xl px-6 pb-12 pt-8 md:px-10">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Underwriting Output</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900 md:text-4xl">Decision Report</h1>
          <p className="mt-2 text-sm text-slate-600">Generated on {formatTimestamp(submittedAt)}</p>
        </div>
        <button
          type="button"
          onClick={() => {
            clearResultBundle();
            window.location.href = "/apply";
          }}
          className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
        >
          Analyze Another
        </button>
      </header>

      <section className="space-y-5">
        <ExplanationCard explanation={explanation} decisionPayload={process.decision_payload} />

        <CollapsibleSection
          title="Decision Breakdown"
          subtitle="Rule-based and AI decision traces, plus score evidence."
        >
          <DecisionCard
            ruleDecision={process.rule_decision}
            aiDecision={process.ai_decision}
            alignment={process.decision_alignment}
            defaultModel={process.default_model_output}
            anomalyModel={process.anomaly_model_output}
            policyOutput={process.policy_retrieval_output}
            withContainer={false}
            showTitle={false}
          />
        </CollapsibleSection>

        <CollapsibleSection
          title="Data Diagnostics"
          subtitle="Missing fields and suspicious inputs detected during processing."
        >
          <DiagnosticsCard
            missingFields={process.missing_fields}
            suspiciousFields={process.suspicious_fields}
            withContainer={false}
            showTitle={false}
          />
        </CollapsibleSection>
      </section>
    </main>
  );
}
