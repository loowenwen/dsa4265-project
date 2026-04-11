"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { sendChatMessage } from "../../lib/api";
import { clearChatState, loadChatState, saveChatState } from "../../lib/chatStore";
import { loadResultBundle } from "../../lib/resultStore";
import { ChatTranscriptMessage } from "../../types/api";

function makeMessageId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function buildMessage(
  role: "user" | "assistant",
  content: string,
  extras?: Partial<Pick<ChatTranscriptMessage, "citations" | "llm_used">>,
): ChatTranscriptMessage {
  return {
    id: makeMessageId(),
    role,
    content,
    citations: extras?.citations,
    llm_used: extras?.llm_used,
    created_at: new Date().toISOString(),
  };
}

function renderInlineMarkdown(text: string, keyPrefix: string): ReactNode[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter((part) => part.length > 0)
    .map((part, index) => {
      const key = `${keyPrefix}-${index}`;
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return <strong key={key}>{part.slice(2, -2)}</strong>;
      }
      return <span key={key}>{part}</span>;
    });
}

function renderAssistantContent(content: string): ReactNode {
  const normalized = content.replace(/\r/g, "");
  const lines = normalized.split("\n");
  const blocks: ReactNode[] = [];

  let index = 0;
  while (index < lines.length) {
    const line = lines[index].trim();

    if (!line) {
      index += 1;
      continue;
    }

    const numberedMatch = line.match(/^\d+\.\s+(.+)$/);
    if (numberedMatch) {
      const listItems: string[] = [];
      while (index < lines.length) {
        const candidate = lines[index].trim();
        const candidateMatch = candidate.match(/^\d+\.\s+(.+)$/);
        if (!candidateMatch) {
          break;
        }
        listItems.push(candidateMatch[1]);
        index += 1;
      }

      blocks.push(
        <ol key={`ol-${blocks.length}`} className="ml-5 list-decimal space-y-1">
          {listItems.map((item, itemIndex) => (
            <li key={`ol-item-${blocks.length}-${itemIndex}`}>{renderInlineMarkdown(item, `ol-${blocks.length}-${itemIndex}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    const bulletMatch = line.match(/^[-*]\s+(.+)$/);
    if (bulletMatch) {
      const listItems: string[] = [];
      while (index < lines.length) {
        const candidate = lines[index].trim();
        const candidateMatch = candidate.match(/^[-*]\s+(.+)$/);
        if (!candidateMatch) {
          break;
        }
        listItems.push(candidateMatch[1]);
        index += 1;
      }

      blocks.push(
        <ul key={`ul-${blocks.length}`} className="ml-5 list-disc space-y-1">
          {listItems.map((item, itemIndex) => (
            <li key={`ul-item-${blocks.length}-${itemIndex}`}>{renderInlineMarkdown(item, `ul-${blocks.length}-${itemIndex}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    blocks.push(
      <p key={`p-${blocks.length}`} className="whitespace-pre-wrap">
        {renderInlineMarkdown(lines[index], `p-${blocks.length}`)}
      </p>,
    );
    index += 1;
  }

  if (blocks.length === 0) {
    return <p className="whitespace-pre-wrap">{content}</p>;
  }

  return <div className="space-y-1.5">{blocks}</div>;
}

export default function FloatingChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatTranscriptMessage[]>([]);
  const [hasHydrated, setHasHydrated] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [memoryStatus, setMemoryStatus] = useState<string>("No turns yet");

  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const stored = loadChatState();
    if (!stored) {
      setHasHydrated(true);
      return;
    }

    setSessionId(stored.sessionId);
    setMessages(stored.messages);
    const assistantTurns = stored.messages.filter((message) => message.role === "assistant").length;
    setMemoryStatus(
      assistantTurns > 0
        ? `${assistantTurns} turn${assistantTurns === 1 ? "" : "s"}`
        : "No turns yet",
    );
    setHasHydrated(true);
  }, []);

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    saveChatState({
      sessionId,
      messages,
    });
  }, [hasHydrated, sessionId, messages]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading, isOpen]);

  const hasMessages = useMemo(() => messages.length > 0, [messages.length]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = input.trim();
    if (!trimmed || isLoading) {
      return;
    }

    const activeSessionId = sessionId;
    const userMessage = buildMessage("user", trimmed);

    setError(null);
    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const latestResult = loadResultBundle();
      const decisionPayload = latestResult?.process?.decision_payload ?? null;

      const response = await sendChatMessage({
        message: trimmed,
        session_id: activeSessionId,
        decision_payload: decisionPayload,
      });

      setSessionId(response.session_id);
      setMemoryStatus(
        `${response.memory.turn_count} turn${response.memory.turn_count === 1 ? "" : "s"}${
          response.memory.truncated ? " (oldest trimmed)" : ""
        }`,
      );
      setMessages((previous) => [
        ...previous,
        buildMessage("assistant", response.answer, {
          citations: response.citations,
          llm_used: response.llm_used,
        }),
      ]);
    } catch {
      setError("Unable to reach chat service. Please retry.");
      setMessages((previous) => [
        ...previous,
        buildMessage(
          "assistant",
          "I couldn't process that request right now. Please retry in a moment.",
          { llm_used: false },
        ),
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setSessionId(null);
    setMessages([]);
    setInput("");
    setError(null);
    setMemoryStatus("No turns yet");
    clearChatState();
  };

  if (!isOpen) {
    return (
      <div className="fixed bottom-5 right-5 z-50">
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="h-14 w-14 rounded-full bg-slate-900 text-sm font-semibold text-white shadow-[0_20px_35px_-20px_rgba(15,23,42,0.7)] transition hover:bg-slate-800"
          aria-label="Open policy chat"
        >
          Chat
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-3 z-50 w-[calc(100vw-1.5rem)] sm:bottom-5 sm:right-5 sm:w-[24rem]">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_28px_60px_-30px_rgba(15,23,42,0.55)]">
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Policy Assistant</p>
            <p className="mt-1 text-xs text-slate-600">Memory: {memoryStatus}</p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleNewChat}
              className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700"
            >
              New
            </button>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="h-7 w-7 rounded-full border border-slate-300 bg-white text-sm font-semibold text-slate-700"
              aria-label="Minimize chat"
            >
              -
            </button>
          </div>
        </header>

        <div className="max-h-[21rem] min-h-[14rem] space-y-3 overflow-y-auto bg-slate-50/70 px-3 py-3">
          {hasMessages ? (
            messages.map((message) => (
              <article
                key={message.id}
                className={`max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-6 ${
                  message.role === "user"
                    ? "ml-auto bg-slate-900 text-white"
                    : "border border-slate-200 bg-white text-slate-900"
                }`}
              >
                {message.role === "assistant" ? (
                  renderAssistantContent(message.content)
                ) : (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                )}

                {message.role === "assistant" ? (
                  <div className="mt-2 space-y-1.5">
                    <p className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                      {message.llm_used ? "RAG + LLM" : "RAG fallback"}
                    </p>

                    {message.citations && message.citations.length > 0 ? (
                      <ul className="space-y-1.5 text-[11px] text-slate-600">
                        {message.citations.map((citation) => (
                          <li
                            key={`${message.id}-${citation.chunk_id}`}
                            className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1"
                          >
                            <p className="font-semibold text-slate-700">{citation.chunk_id}</p>
                            <p className="mt-0.5 max-h-10 overflow-hidden">{citation.snippet}</p>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
              </article>
            ))
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white px-3 py-3 text-xs text-slate-600">
              Ask policy questions like "When should an application go to manual review?"
            </div>
          )}

          {isLoading ? (
            <div className="inline-flex rounded-full border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-600">
              Thinking...
            </div>
          ) : null}

          <div ref={transcriptEndRef} />
        </div>

        <form className="space-y-2 border-t border-slate-200 bg-white px-3 py-3" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask a policy question..."
            rows={2}
            className="w-full resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500"
            disabled={isLoading}
          />

          <div className="flex items-center justify-between gap-2">
            {error ? <p className="text-xs text-rose-700">{error}</p> : <span />}

            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="rounded-full bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              Send
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
