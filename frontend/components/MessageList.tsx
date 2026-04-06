"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/types/chat";
import MessageBubble from "./MessageBubble";

const SUGGESTED_PROMPTS = [
  {
    label: "☠️ Theobromine toxicosis",
    query: "Theobromine toxicosis in dogs: dose-response, clinical signs, and management",
  },
  {
    label: "🫁 Feline bronchial disease",
    query: "Feline bronchial disease: differential diagnosis and diagnostic workup",
  },
  {
    label: "🧬 Canine atopic dermatitis",
    query: "Canine atopic dermatitis: immunopathogenesis and current treatment options",
  },
  {
    label: "🍇 Grape nephrotoxicity",
    query: "Grape and raisin nephrotoxicity in dogs: proposed mechanism and clinical course",
  },
];

interface MessageListProps {
  messages: Message[];
  onSend: (query: string) => void;
}

export default function MessageList({ messages, onSend }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="text-center space-y-6 max-w-lg w-full">
          <div className="space-y-1">
            <p className="text-4xl">🐾</p>
            <p className="text-gray-600 font-medium">
              Ask a clinical question to access veterinary literature evidence.
            </p>
            <p className="text-xs text-gray-400">
              Powered by ScienceDirect · Springer Nature · Claude AI
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SUGGESTED_PROMPTS.map((p) => (
              <button
                key={p.label}
                onClick={() => onSend(p.query)}
                className="text-left rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 transition-colors shadow-sm"
              >
                <span className="font-medium">{p.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
