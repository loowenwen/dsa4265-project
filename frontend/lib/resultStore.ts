import { ExplanationResponse, ProcessResponse } from "../types/api";

export const RESULT_STORAGE_KEY = "applicant_processor_latest_result";
export const RESULT_HISTORY_STORAGE_KEY = "applicant_processor_result_history";
export const MAX_RESULT_HISTORY = 6;
const DUPLICATE_TIME_WINDOW_MS = 2 * 60 * 1000;

export type StoredResultBundle = {
  submittedAt: string;
  process: ProcessResponse;
  explanation: ExplanationResponse;
};

function safeTimestamp(iso: string): number | null {
  const ts = new Date(iso).getTime();
  return Number.isNaN(ts) ? null : ts;
}

function buildBundleFingerprint(bundle: StoredResultBundle): string {
  return JSON.stringify({
    overall_decision: bundle.explanation.overall_decision,
    summary: bundle.explanation.summary,
    key_metrics: bundle.explanation.key_metrics,
    supporting_evidence: bundle.explanation.supporting_evidence,
    cautionary_evidence: bundle.explanation.cautionary_evidence,
    limitations: bundle.explanation.limitations,
    decision_payload: bundle.process.decision_payload,
  });
}

function isLikelyDuplicateBundle(a: StoredResultBundle, b: StoredResultBundle): boolean {
  if (buildBundleFingerprint(a) !== buildBundleFingerprint(b)) {
    return false;
  }

  const aTime = safeTimestamp(a.submittedAt);
  const bTime = safeTimestamp(b.submittedAt);
  if (aTime === null || bTime === null) {
    return false;
  }

  return Math.abs(aTime - bTime) <= DUPLICATE_TIME_WINDOW_MS;
}

function dedupeHistory(history: StoredResultBundle[]): StoredResultBundle[] {
  const deduped: StoredResultBundle[] = [];
  for (const item of history) {
    const alreadyExists = deduped.some((existing) => isLikelyDuplicateBundle(existing, item));
    if (!alreadyExists) {
      deduped.push(item);
    }
  }
  return deduped;
}

function parseStoredBundle(raw: string): StoredResultBundle | null {
  try {
    const parsed = JSON.parse(raw) as StoredResultBundle;
    if (!parsed || typeof parsed.submittedAt !== "string") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function parseStoredHistory(raw: string): StoredResultBundle[] {
  try {
    const parsed = JSON.parse(raw) as StoredResultBundle[];
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(
      (item) => item && typeof item === "object" && typeof item.submittedAt === "string",
    );
  } catch {
    return [];
  }
}

export function loadResultHistory(): StoredResultBundle[] {
  if (typeof window === "undefined") {
    return [];
  }

  const historyRaw = window.sessionStorage.getItem(RESULT_HISTORY_STORAGE_KEY);
  if (historyRaw) {
    return dedupeHistory(parseStoredHistory(historyRaw));
  }

  // Backward compatibility with old single-result storage.
  const latestRaw = window.sessionStorage.getItem(RESULT_STORAGE_KEY);
  if (!latestRaw) {
    return [];
  }

  const parsed = parseStoredBundle(latestRaw);
  return parsed ? dedupeHistory([parsed]) : [];
}

export function saveResultBundle(bundle: StoredResultBundle): void {
  if (typeof window === "undefined") {
    return;
  }

  const existing = loadResultHistory().filter(
    (item) => item.submittedAt !== bundle.submittedAt && !isLikelyDuplicateBundle(item, bundle),
  );
  const nextHistory = dedupeHistory([bundle, ...existing]).slice(0, MAX_RESULT_HISTORY);

  window.sessionStorage.setItem(RESULT_HISTORY_STORAGE_KEY, JSON.stringify(nextHistory));
  // Keep latest-result key for compatibility with existing consumers.
  window.sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(bundle));
}

export function loadResultBundle(): StoredResultBundle | null {
  const history = loadResultHistory();
  return history.length > 0 ? history[0] : null;
}

export function clearResultBundle(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(RESULT_HISTORY_STORAGE_KEY);
  window.sessionStorage.removeItem(RESULT_STORAGE_KEY);
}
