import { ExplanationResponse, ProcessResponse } from "../types/api";

export const RESULT_STORAGE_KEY = "applicant_processor_latest_result";

export type StoredResultBundle = {
  submittedAt: string;
  process: ProcessResponse;
  explanation: ExplanationResponse;
};

export function saveResultBundle(bundle: StoredResultBundle): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(bundle));
}

export function loadResultBundle(): StoredResultBundle | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.sessionStorage.getItem(RESULT_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StoredResultBundle;
  } catch {
    return null;
  }
}

export function clearResultBundle(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(RESULT_STORAGE_KEY);
}
