"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuthContext } from "@/components/AuthProvider";
import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";
import DisclaimerFooter from "./DisclaimerFooter";
import InputBar from "./InputBar";
import MessageList from "./MessageList";
import Sidebar from "./Sidebar";

export default function ChatPage() {
  const { user, logout } = useAuthContext();
  const { conversations, fetchConversations, loadConversation, deleteConversation } =
    useConversations();

  const { messages, isLoading, error, sendMessage, resetMessages, loadMessages } =
    useChat(() => {
      // Refresh sidebar after each completed chat
      fetchConversations();
    });

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  const handleNewChat = () => {
    resetMessages();
    setActiveConversationId(null);
    setSidebarOpen(false);
  };

  const handleSelectConversation = async (id: string) => {
    const conv = await loadConversation(id);
    if (conv) {
      loadMessages(conv.messages);
      setActiveConversationId(id);
    }
    setSidebarOpen(false);
  };

  const handleDeleteConversation = async (id: string) => {
    await deleteConversation(id);
    if (activeConversationId === id) handleNewChat();
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        user={user}
        onLogout={logout}
      />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="bg-white border-b px-4 py-3 flex items-center gap-3 shadow-sm">
          {/* Mobile hamburger */}
          <button
            className="md:hidden text-gray-500 hover:text-gray-800 text-xl leading-none"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            ☰
          </button>

          <Link
            href="/"
            className="flex items-center gap-3 hover:opacity-80 transition-opacity"
          >
            <span className="text-2xl">🐾</span>
            <div>
              <h1 className="font-bold text-gray-800 text-lg leading-tight">
                VetChat AI
              </h1>
              <p className="text-xs text-gray-500">
                Evidence-based clinical reference for veterinary professionals
              </p>
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
    </div>
  );
}
