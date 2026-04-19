"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/types/chat";
import MessageBubble from "./MessageBubble";

const SUGGESTED_PROMPTS = [
  {
    label: "🦠 Feline infectious peritonitis",
    query: "Feline infectious peritonitis: pathogenesis, diagnosis, and novel antiviral treatment protocols",
  },
  {
    label: "🩸 Immune-mediated haemolytic anaemia",
    query: "Canine immune-mediated haemolytic anaemia: diagnostic criteria and immunosuppressive treatment protocols",
  },
  {
    label: "🔥 Canine pancreatitis",
    query: "Canine pancreatitis: severity scoring, diagnostic approach, and evidence-based management",
  },
  {
    label: "🐱 Feline hyperthyroidism",
    query: "Feline hyperthyroidism: comparison of treatment options including radioiodine, methimazole, and thyroidectomy",
  },
  {
    label: "🧠 Canine cognitive dysfunction",
    query: "Canine cognitive dysfunction syndrome: pathophysiology, diagnosis criteria, and pharmacological management",
  },
  {
    label: "🦴 Cranial cruciate ligament rupture",
    query: "Canine cranial cruciate ligament rupture: TPLO versus conservative management evidence",
  },
  {
    label: "💊 Antimicrobial stewardship",
    query: "Antimicrobial stewardship in small animal practice: resistance patterns and empirical therapy guidelines",
  },
  {
    label: "☠️ NSAID toxicity small animals",
    query: "NSAID toxicity in dogs and cats: mechanism, clinical signs, decontamination and management",
  },
];

const DELAY_CLASSES = [
  "",
  "animation-delay-75",
  "animation-delay-150",
  "animation-delay-225",
  "animation-delay-300",
  "animation-delay-375",
  "animation-delay-450",
  "animation-delay-525",
];

interface MessageListProps {
  messages: Message[];
  onSend: (query: string) => void;
  isAuthenticated?: boolean;
  onAuthGate?: (query: string) => void;
  onRetry?: (originalQuery?: string, messageId?: string) => void;
  onExpandSearch?: (originalQuery?: string, messageId?: string) => void;
}

export default function MessageList({
  messages,
  onSend,
  isAuthenticated,
  onAuthGate,
  onRetry,
  onExpandSearch,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Only auto-scroll while a response is loading (isLoading messages present),
  // not after the final answer arrives — so the user stays at the top of the answer.
  useEffect(() => {
    const hasLoading = messages.some((m) => m.isLoading);
    if (hasLoading) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handlePromptClick = (query: string) => {
    if (!isAuthenticated && onAuthGate) {
      onAuthGate(query);
    } else {
      onSend(query);
    }
  };

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-3 py-6 animate-fade-in overflow-y-auto">
        <div className="text-center space-y-5 w-full max-w-2xl">
          <div className="space-y-1 animate-slide-up">
            <p className="text-3xl sm:text-4xl">🐾</p>
            <p className="text-gray-600 font-medium text-sm sm:text-base">
              Ask any clinical question — Arlo searches peer-reviewed veterinary literature for you.
            </p>
            <p className="text-xs text-gray-400">
              Powered by ScienceDirect · Springer Nature · Taylor &amp; Francis
            </p>
          </div>
          {/* 1 col on mobile, 2 cols on sm+ */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
            {SUGGESTED_PROMPTS.map((p, i) => (
              <button
                key={p.label}
                onClick={() => handlePromptClick(p.query)}
                aria-label={`Ask: ${p.query}`}
                className={`text-left rounded-xl border border-gray-200 bg-white px-3 py-2.5 sm:px-4 sm:py-3 text-sm text-gray-700 hover:border-teal-400 hover:bg-teal-50 hover:text-teal-700 active:bg-teal-100 transition-colors shadow-sm animate-slide-up ${DELAY_CLASSES[i] ?? ""}`}
              >
                <span className="font-medium leading-snug block">{p.label}</span>
              </button>
            ))}
          </div>
          {!isAuthenticated && (
            <p className="text-xs text-gray-400 animate-fade-in animation-delay-525 px-2">
              Sign in to start searching peer-reviewed veterinary literature
            </p>
          )}
        </div>
      </div>
    );
  }

  // An assistant bubble is a follow-up if an earlier assistant message exists in this chat
  let seenAssistant = false;
  return (
    <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-4 space-y-4">
      {messages.map((msg) => {
        const isFollowUp = msg.role === "assistant" && seenAssistant;
        if (msg.role === "assistant") seenAssistant = true;
        return (
          <MessageBubble
            key={msg.id}
            message={msg}
            isFollowUp={isFollowUp}
            onRetry={(q) => onRetry?.(q, msg.id)}
            onExpandSearch={(q) => onExpandSearch?.(q, msg.id)}
          />
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
