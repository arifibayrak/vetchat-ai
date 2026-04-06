"use client";

import { useAuthContext } from "@/components/AuthProvider";
import ChatPage from "@/components/ChatPage";

export default function Home() {
  const { isLoading } = useAuthContext();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center gap-2 text-gray-400 text-sm animate-fade-in">
          <span className="text-xl">🐾</span>
          <span>Loading…</span>
        </div>
      </div>
    );
  }

  return <ChatPage />;
}
