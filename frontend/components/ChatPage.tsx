"use client";

import { useChat } from "@/hooks/useChat";
import Link from "next/link";
import DisclaimerFooter from "./DisclaimerFooter";
import InputBar from "./InputBar";
import MessageList from "./MessageList";

export default function ChatPage() {
  const { messages, isLoading, error, sendMessage } = useChat();

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-3 flex items-center gap-3 shadow-sm">
        <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <span className="text-2xl">🐾</span>
          <div>
            <h1 className="font-bold text-gray-800 text-lg leading-tight">VetChat AI</h1>
            <p className="text-xs text-gray-500">Citation-first veterinary literature assistant</p>
          </div>
        </Link>
      </header>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Message thread */}
      <MessageList messages={messages} onSend={sendMessage} />

      {/* Input + footer */}
      <InputBar onSend={sendMessage} disabled={isLoading} />
      <DisclaimerFooter />
    </div>
  );
}
