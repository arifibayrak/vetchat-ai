"use client";

import { useCallback, useState } from "react";
import type { ChatResponse, EmergencyPreliminary, FlowData, Message, ProgressStep } from "@/types/chat";
import { useAuthContext } from "@/components/AuthProvider";

let _idCounter = 0;
export const uid = () => String(++_idCounter);

const SLOW_QUERY_MS = 45_000;

type HistoryTurn = { role: "user" | "assistant"; content: string };

async function streamChat(
  query: string,
  history: HistoryTurn[],
  token: string | null,
  onProgress: (step: ProgressStep) => void,
  onResult: (response: ChatResponse) => void,
  onError: (msg: string) => void,
  onFlow: (flow: FlowData) => void,
  onEmergencyPreliminary: (card: EmergencyPreliminary) => void,
  onSlowQuery: () => void,
) {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch("/api/chat", {
    method: "POST",
    headers,
    body: JSON.stringify({ query, history }),
  });

  if (!res.ok || !res.body) {
    onError(`Server error: ${res.status}`);
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

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return;
    setError(null);

    const userMsg: Message = {
      id: uid(),
      role: "user",
      content: query,
      citations: [],
      liveResources: [],
      emergency: false,
      resources: [],
    };

    const assistantId = uid();
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
    };

    // Build history from prior completed turns in this session
    const history: HistoryTurn[] = messages
      .filter((m) => !m.isLoading && m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setIsLoading(true);

    await streamChat(
      query,
      history,
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
      // onResult
      (response) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: response.answer,
                  citations: response.citations,
                  liveResources: response.live_resources ?? [],
                  emergency: response.emergency,
                  resources: response.resources,
                  isLoading: false,
                  steps: undefined,
                  retrievalQuality: response.retrieval_quality,
                  totalSources: response.total_sources,
                  citedCount: response.cited_count,
                }
              : msg,
          ),
        );
        setIsLoading(false);
        onComplete?.();
      },
      // onError
      (errMsg) => {
        setError(errMsg);
        setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
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
    );
  }, [isLoading, token, onComplete, messages]);

  return { messages, isLoading, error, sendMessage, resetMessages, loadMessages };
}
