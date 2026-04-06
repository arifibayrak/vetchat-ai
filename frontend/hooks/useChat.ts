"use client";

import { useCallback, useState } from "react";
import type { ChatResponse, Message, ProgressStep } from "@/types/chat";

let _idCounter = 0;
const uid = () => String(++_idCounter);

async function streamChat(
  query: string,
  onProgress: (step: ProgressStep) => void,
  onResult: (response: ChatResponse) => void,
  onError: (msg: string) => void,
) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
        }
      } catch {
        // malformed line — skip
      }
    }
  }
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      // onProgress — update the loading bubble with new step
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
              : msg
          )
        );
      },
      // onResult — replace loading bubble with final answer
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
              : msg
          )
        );
        setIsLoading(false);
      },
      // onError
      (errMsg) => {
        setError(errMsg);
        setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
        setIsLoading(false);
      },
    );
  }, [isLoading]);

  return { messages, isLoading, error, sendMessage };
}
