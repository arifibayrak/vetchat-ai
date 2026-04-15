"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthContext } from "@/components/AuthProvider";
import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";
import AuthGateModal from "./AuthGateModal";
import DisclaimerFooter from "./DisclaimerFooter";
import DogLogo from "./DogLogo";
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

          <Link
            href="/"
            className="flex items-center gap-3 hover:opacity-80 transition-opacity"
          >
            <DogLogo size={36} />
            <div>
              <h1 className="font-bold text-teal-400 text-lg leading-tight">
                Lenny
              </h1>
              <p className="text-xs text-slate-400">
                Evidence-based clinical reference for veterinary professionals
              </p>
            </div>
          </Link>

          {!user && (
            <div className="ml-auto flex items-center gap-2">
              <Link
                href="/login"
                className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
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
