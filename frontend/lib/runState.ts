export const ACTIVE_RUN_STORAGE_KEY = "applicant_processor_active_run";
export const ACTIVE_RUN_TTL_MS = 10 * 60 * 1000;

export type ActiveRunStatus = "running" | "completed" | "failed";

export type ActiveRunState = {
  runId: string;
  startedAt: string;
  updatedAt: string;
  progress: number;
  stageLabel: string;
  status: ActiveRunStatus;
};

function parseActiveRun(raw: string): ActiveRunState | null {
  try {
    const parsed = JSON.parse(raw) as ActiveRunState;
    if (
      !parsed ||
      typeof parsed !== "object" ||
      typeof parsed.runId !== "string" ||
      typeof parsed.startedAt !== "string" ||
      typeof parsed.updatedAt !== "string" ||
      typeof parsed.progress !== "number" ||
      typeof parsed.stageLabel !== "string" ||
      typeof parsed.status !== "string"
    ) {
      return null;
    }

    if (!["running", "completed", "failed"].includes(parsed.status)) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}

function makeRunId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createActiveRun(progress = 0, stageLabel = "Starting analysis"): ActiveRunState {
  const now = new Date().toISOString();
  return {
    runId: makeRunId(),
    startedAt: now,
    updatedAt: now,
    progress,
    stageLabel,
    status: "running",
  };
}

export function loadActiveRun(): ActiveRunState | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.sessionStorage.getItem(ACTIVE_RUN_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  return parseActiveRun(raw);
}

export function saveActiveRun(run: ActiveRunState): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(ACTIVE_RUN_STORAGE_KEY, JSON.stringify(run));
}

export function clearActiveRun(expectedRunId?: string): void {
  if (typeof window === "undefined") {
    return;
  }

  if (!expectedRunId) {
    window.sessionStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
    return;
  }

  const current = loadActiveRun();
  if (!current || current.runId === expectedRunId) {
    window.sessionStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
  }
}

export function isActiveRunFresh(run: ActiveRunState): boolean {
  const updatedAt = new Date(run.updatedAt).getTime();
  if (Number.isNaN(updatedAt)) {
    return false;
  }

  return Date.now() - updatedAt <= ACTIVE_RUN_TTL_MS;
}
