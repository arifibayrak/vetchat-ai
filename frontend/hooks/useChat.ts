"use client";

import { useCallback, useState } from "react";
import type { ChatResponse, FlowData, Message, ProgressStep } from "@/types/chat";
import { useAuthContext } from "@/components/AuthProvider";

let _idCounter = 0;
export const uid = () => String(++_idCounter);

async function streamChat(
  query: string,
  token: string | null,
  onProgress: (step: ProgressStep) => void,
  onResult: (response: ChatResponse) => void,
  onError: (msg: string) => void,
  onFlow: (flow: FlowData) => void,
) {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch("/api/chat", {
    method: "POST",
    headers,
    body: JSON.stringify({ query }),
  });

  if (!res.ok || !res.body) {
    onError(`Server error: ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

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
          onResult(event.payload as ChatResponse);
        } else if (event.type === "flow") {
          onFlow(event.payload as FlowData);
        }
      } catch {
        // malformed line — skip
      }
    }
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

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setIsLoading(true);

    await streamChat(
      query,
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
    );
  }, [isLoading, token, onComplete]);

  return { messages, isLoading, error, sendMessage, resetMessages, loadMessages };
}
