"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthContext } from "@/components/AuthProvider";
import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";
import AuthGateModal from "./AuthGateModal";
import DisclaimerFooter from "./DisclaimerFooter";
import InputBar from "./InputBar";
import MessageList from "./MessageList";
import Sidebar from "./Sidebar";

export default function ChatPage() {
  const { user, logout } = useAuthContext();
  const router = useRouter();
  const { conversations, fetchConversations, loadConversation, deleteConversation } =
    useConversations();

  const { messages, isLoading, error, sendMessage, resetMessages, loadMessages } =
    useChat(() => {
      fetchConversations();
    });

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [authGateQuery, setAuthGateQuery] = useState<string | null>(null);

  useEffect(() => {
    if (user) fetchConversations();
  }, [user]);

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

  const handleLogout = () => {
    router.push("/sign-out");
  };

  const handleSendOrGate = (query: string) => {
    if (!user) {
      setAuthGateQuery(query);
      return;
    }
    sendMessage(query);
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {authGateQuery !== null && (
        <AuthGateModal
          query={authGateQuery}
          onClose={() => setAuthGateQuery(null)}
        />
      )}

      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        user={user}
        onLogout={handleLogout}
      />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="bg-slate-900 border-b border-slate-700 px-4 py-3 flex items-center gap-3 shadow-sm">
          <button
            className="md:hidden text-slate-400 hover:text-white text-xl leading-none"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            ☰
          </button>

          <Link href="/" className="flex items-center gap-2 hover:opacity-90 transition-opacity group">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M12 1 L23 23 L1 23 Z M12 6 L19 23 L5 23 Z M5 15 L19 15 L19 18 L5 18 Z"
                fill="#2dd4bf"
              />
            </svg>
            <h1 className="text-[17px] font-semibold text-white tracking-tight group-hover:text-teal-100 transition-colors">
              Arlo
            </h1>
          </Link>

          {!user && (
            <div className="ml-auto flex items-center gap-2">
              <Link
                href="/login"
                className="text-sm text-slate-300 hover:text-white transition-colors"
              >
                Sign in
              </Link>
              <Link
                href="/register"
                className="text-sm bg-teal-600 hover:bg-teal-700 text-white rounded-lg px-3 py-1.5 font-medium transition-colors"
              >
                Register
              </Link>
            </div>
          )}
        </header>

        {error && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700 animate-fade-in">
            {error}
          </div>
        )}

        <MessageList
          messages={messages}
          onSend={handleSendOrGate}
          isAuthenticated={!!user}
          onAuthGate={(q) => setAuthGateQuery(q)}
        />

        <InputBar
          onSend={handleSendOrGate}
          disabled={isLoading}
        />
        <DisclaimerFooter />
      </div>
    </div>
  );
}
