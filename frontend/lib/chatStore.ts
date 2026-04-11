import { ChatTranscriptMessage } from "../types/api";

const CHAT_STORAGE_KEY = "underwriting_policy_chat_state";

export type StoredChatState = {
  sessionId: string | null;
  messages: ChatTranscriptMessage[];
};

export function saveChatState(state: StoredChatState): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(state));
}

export function loadChatState(): StoredChatState | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.sessionStorage.getItem(CHAT_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as StoredChatState;
    if (!Array.isArray(parsed.messages)) {
      return null;
    }
    return {
      sessionId: parsed.sessionId ?? null,
      messages: parsed.messages,
    };
  } catch {
    return null;
  }
}

export function clearChatState(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(CHAT_STORAGE_KEY);
}
