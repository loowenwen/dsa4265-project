"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import CollapsibleSection from "../components/CollapsibleSection";
import DecisionCard from "../components/DecisionCard";
import DiagnosticsCard from "../components/DiagnosticsCard";
import ExplanationCard from "../components/ExplanationCard";
import type { StoredResultBundle } from "../../lib/resultStore";
import {
  MAX_RESULT_HISTORY,
  clearResultBundle,
  loadResultHistory,
} from "../../lib/resultStore";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return date.toLocaleString();
}

function formatDecision(decision: string): string {
  return decision
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function ResultPage() {
  const [history, setHistory] = useState<StoredResultBundle[] | undefined>(undefined);
  const [activeSubmittedAt, setActiveSubmittedAt] = useState<string | null>(null);

  useEffect(() => {
    const loaded = loadResultHistory();
    setHistory(loaded);
    setActiveSubmittedAt(loaded[0]?.submittedAt ?? null);
  }, []);

  const activeBundle = useMemo(() => {
    if (!history || history.length === 0) {
      return null;
    }

    if (!activeSubmittedAt) {
      return history[0];
    }

    return history.find((item) => item.submittedAt === activeSubmittedAt) ?? history[0];
  }, [history, activeSubmittedAt]);

  if (history === undefined) {
    return (
      <main className="mx-auto max-w-7xl px-6 pb-12 pt-8 md:px-10">
        <section className="surface-card p-8 text-sm text-slate-600">Loading result history...</section>
      </main>
    );
  }

  if (!activeBundle) {
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

  const { process, explanation, submittedAt } = activeBundle;

  return (
    <main className="mx-auto max-w-7xl px-6 pb-12 pt-8 md:px-10">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Underwriting Output</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900 md:text-4xl">Decision Report</h1>
          <p className="mt-2 text-sm text-slate-600">Generated on {formatTimestamp(submittedAt)}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              window.location.href = "/apply";
            }}
            className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
          >
            Analyze Another
          </button>
          <button
            type="button"
            onClick={() => {
              clearResultBundle();
              setHistory([]);
              setActiveSubmittedAt(null);
            }}
            className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
          >
            Clear History
          </button>
        </div>
      </header>

      <section className="surface-card mb-5 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-slate-900">Recent Runs</h2>
          <p className="text-xs uppercase tracking-[0.14em] text-slate-500">
            Showing up to {MAX_RESULT_HISTORY} runs
          </p>
        </div>

        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {history.map((item) => {
            const isActive = item.submittedAt === submittedAt;
            return (
              <button
                key={item.submittedAt}
                type="button"
                onClick={() => setActiveSubmittedAt(item.submittedAt)}
                className={`rounded-xl border px-4 py-3 text-left transition ${
                  isActive
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-300 bg-white text-slate-800 hover:border-slate-400"
                }`}
              >
                <p className={`text-xs uppercase tracking-[0.12em] ${isActive ? "text-slate-200" : "text-slate-500"}`}>
                  {formatDecision(item.explanation.overall_decision)}
                </p>
                <p className="mt-1 text-sm font-medium">{formatTimestamp(item.submittedAt)}</p>
              </button>
            );
          })}
        </div>
      </section>

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
