"use client";

import { useCallback, useState } from "react";
import type { ChatResponse, EmergencyPreliminary, FlowData, Message, ProgressStep } from "@/types/chat";
import { useAuthContext } from "@/components/AuthProvider";

let _idCounter = 0;
export const uid = () => String(++_idCounter);

const SLOW_QUERY_MS = 45_000;
// Auto-retry transient 5xx once before surfacing a failure bubble. The short
// pause lets Railway finish warming up the container without forcing the user
// to click Retry themselves for the common cold-start case.
const AUTO_RETRY_STATUSES = new Set([502, 503, 504]);
const AUTO_RETRY_DELAY_MS = 1500;

type HistoryTurn = { role: "user" | "assistant"; content: string };

type FailureKind = NonNullable<Message["failureKind"]>;

async function streamChat(
  query: string,
  history: HistoryTurn[],
  priorCitations: unknown[],
  token: string | null,
  onProgress: (step: ProgressStep) => void,
  onResult: (response: ChatResponse) => void,
  onError: (kind: FailureKind, msg: string) => void,
  onFlow: (flow: FlowData) => void,
  onEmergencyPreliminary: (card: EmergencyPreliminary) => void,
  onSlowQuery: () => void,
  onAnswerChunk: (delta: string) => void,
  opts: { attempt?: number } = {},
) {
  const attempt = opts.attempt ?? 0;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch("/api/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({ query, history, prior_citations: priorCitations }),
    });
  } catch {
    // Network failure (offline, DNS, connection reset)
    onError("network", "Lost connection to Arlo. Check your network and retry.");
    return;
  }

  if (!res.ok || !res.body) {
    const ct = res.headers.get("content-type") || "";
    if (attempt === 0 && AUTO_RETRY_STATUSES.has(res.status)) {
      // Transparent auto-retry — common during Railway cold starts.
      await new Promise((r) => setTimeout(r, AUTO_RETRY_DELAY_MS));
      return streamChat(
        query, history, priorCitations, token,
        onProgress, onResult, onError, onFlow, onEmergencyPreliminary, onSlowQuery, onAnswerChunk,
        { attempt: attempt + 1 },
      );
    }
    if (AUTO_RETRY_STATUSES.has(res.status) || ct.startsWith("text/html")) {
      onError("server", "Arlo's backend is still starting up. Please retry in ~30 seconds.");
    } else {
      onError("server", `Server returned ${res.status}. Please retry.`);
    }
    return;
  }

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("text/event-stream") && ct.startsWith("text/html")) {
    onError("server", "Arlo's backend is still starting up. Please retry in ~30 seconds.");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let resultReceived = false;

  const slowTimer = setTimeout(() => {
    if (!resultReceived) onSlowQuery();
  }, SLOW_QUERY_MS);

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === "progress") {
            onProgress({ step: event.step, label: event.label, icon: event.icon, done: false });
          } else if (event.type === "answer_chunk") {
            onAnswerChunk(event.delta as string);
          } else if (event.type === "result") {
            resultReceived = true;
            clearTimeout(slowTimer);
            onResult(event.payload as ChatResponse);
          } else if (event.type === "flow") {
            onFlow(event.payload as FlowData);
          } else if (event.type === "emergency_preliminary") {
            onEmergencyPreliminary(event.payload as EmergencyPreliminary);
          }
        } catch {
          // malformed line — skip
        }
      }
    }

    // Stream closed without a `result` event — treat as a timeout so the
    // user sees a recoverable failure bubble rather than a frozen loading
    // state or silently-removed answer.
    if (!resultReceived) {
      onError("timeout", "The connection closed before an answer was produced.");
    }
  } catch {
    onError("network", "The connection dropped mid-stream. Retry to continue.");
  } finally {
    clearTimeout(slowTimer);
  }
}

export function useChat(onComplete?: () => void) {
  const { token } = useAuthContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const loadMessages = useCallback((rawMessages: Array<{
    role: "user" | "assistant";
    content: string;
    citations: Message["citations"];
    live_resources: Message["liveResources"];
    emergency: boolean;
    resources: string[];
  }>) => {
    const converted: Message[] = rawMessages.map((m) => ({
      id: uid(),
      role: m.role,
      content: m.content,
      citations: m.citations ?? [],
      liveResources: m.live_resources ?? [],
      emergency: m.emergency ?? false,
      resources: m.resources ?? [],
    }));
    setMessages(converted);
    setError(null);
  }, []);

  const sendMessage = useCallback(async (
    query: string,
    opts: { expand?: boolean; replaceMessageId?: string } = {},
  ) => {
    if (!query.trim() || isLoading) return;
    setError(null);

    // When a Retry/Expand button is clicked, replace the prior failure bubble
    // in place rather than appending another user turn.
    const assistantId = uid();
    const isReplacement = !!opts.replaceMessageId;

    const loadingMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      citations: [],
      liveResources: [],
      emergency: false,
      resources: [],
      isLoading: true,
      steps: [],
      currentStep: 0,
      originalQuery: query,
    };

    // Build history from prior completed turns (skip failure bubbles)
    const historySource = messages.filter(
      (m) => !m.isLoading && !m.failureKind && m.content,
    );
    const history: HistoryTurn[] = historySource.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    // Pull citations from the most recent completed assistant turn so the
    // backend can reuse them instead of re-running retrieval on follow-ups.
    // On "expand search", deliberately clear prior_citations so the backend
    // does a fresh full retrieval instead of reusing the cached context.
    const lastAssistant = [...messages]
      .reverse()
      .find((m) => m.role === "assistant" && !m.isLoading && !m.failureKind && m.citations?.length);
    const priorCitations = opts.expand ? [] : (lastAssistant?.citations ?? []);

    const effectiveQuery = opts.expand
      ? `${query}\n\n(Expand search: pull a fresh set of sources even if similar was asked recently.)`
      : query;

    setMessages((prev) => {
      if (isReplacement) {
        return prev.map((m) => (m.id === opts.replaceMessageId ? loadingMsg : m));
      }
      const userMsg: Message = {
        id: uid(),
        role: "user",
        content: query,
        citations: [],
        liveResources: [],
        emergency: false,
        resources: [],
      };
      return [...prev, userMsg, loadingMsg];
    });
    setIsLoading(true);

    await streamChat(
      effectiveQuery,
      history,
      priorCitations,
      token,
      // onProgress
      (step) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  steps: [
                    ...(msg.steps ?? []).map((s) => ({ ...s, done: true })),
                    step,
                  ],
                  currentStep: step.step,
                }
              : msg,
          ),
        );
      },
      // onResult — finalises citations + metadata.
      (response) => {
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.id !== assistantId) return msg;
            const finalContent = msg.content && msg.content.length > 0
              ? (response.answer.length > msg.content.length * 0.5 ? response.answer : msg.content)
              : response.answer;
            return {
              ...msg,
              content: finalContent,
              citations: response.citations,
              liveResources: response.live_resources ?? [],
              emergency: response.emergency,
              resources: response.resources,
              isLoading: false,
              isStreaming: false,
              steps: undefined,
              retrievalQuality: response.retrieval_quality,
              totalSources: response.total_sources,
              citedCount: response.cited_count,
              evidenceMode: response.evidence_mode,
              fallbackKind: response.fallback_kind,
              evidenceCounts: response.evidence_counts,
              hiddenReferences: response.hidden_references ?? [],
              failureKind: undefined,
              failureMessage: undefined,
            };
          }),
        );
        setIsLoading(false);
        onComplete?.();
      },
      // onError — convert the loading bubble INTO a failure bubble so the
      // user can click Retry or Expand search. Never silently remove it.
      (kind, errMsg) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  isLoading: false,
                  isStreaming: false,
                  steps: undefined,
                  failureKind: kind,
                  failureMessage: errMsg,
                  originalQuery: query,
                }
              : msg,
          ),
        );
        setIsLoading(false);
      },
      // onFlow
      (flow) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId ? { ...msg, flow } : msg,
          ),
        );
      },
      // onEmergencyPreliminary
      (card) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId ? { ...msg, emergencyPreliminary: card } : msg,
          ),
        );
      },
      // onSlowQuery
      () => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId ? { ...msg, isSlowQuery: true } : msg,
          ),
        );
      },
      // onAnswerChunk
      (delta) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: (msg.content ?? "") + delta,
                  isLoading: false,
                  isStreaming: true,
                  steps: undefined,
                }
              : msg,
          ),
        );
      },
    );
  }, [isLoading, token, onComplete, messages]);

  // Retry from a failure bubble — replaces that bubble in place.
  const retryMessage = useCallback((originalQuery?: string, messageId?: string) => {
    if (!originalQuery) return;
    sendMessage(originalQuery, { replaceMessageId: messageId });
  }, [sendMessage]);

  // Expand search — re-ask with fresh retrieval, skipping cached prior_citations.
  const expandSearch = useCallback((originalQuery?: string, messageId?: string) => {
    if (!originalQuery) return;
    sendMessage(originalQuery, { expand: true, replaceMessageId: messageId });
  }, [sendMessage]);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    retryMessage,
    expandSearch,
    resetMessages,
    loadMessages,
  };
}
