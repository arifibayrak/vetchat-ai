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
}

export default function MessageList({ messages, onSend, isAuthenticated, onAuthGate }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
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
      <div className="flex flex-1 items-center justify-center px-4 animate-fade-in">
        <div className="text-center space-y-6 max-w-2xl w-full">
          <div className="space-y-1 animate-slide-up">
            <p className="text-4xl">🐾</p>
            <p className="text-gray-600 font-medium">
              Ask a clinical question to access veterinary literature evidence.
            </p>
            <p className="text-xs text-gray-400">
              Powered by ScienceDirect · Springer Nature · Claude AI
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SUGGESTED_PROMPTS.map((p, i) => (
              <button
                key={p.label}
                onClick={() => handlePromptClick(p.query)}
                className={`text-left rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 transition-colors shadow-sm animate-slide-up ${DELAY_CLASSES[i] ?? ""}`}
              >
                <span className="font-medium">{p.label}</span>
              </button>
            ))}
          </div>
          {!isAuthenticated && (
            <p className="text-xs text-gray-400 animate-fade-in animation-delay-525">
              Sign in to start searching peer-reviewed veterinary literature
            </p>
          )}
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
