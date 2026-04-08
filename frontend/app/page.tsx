"use client";

import { useAuthContext } from "@/components/AuthProvider";
import ChatPage from "@/components/ChatPage";
import LandingPage from "@/components/LandingPage";

export default function Home() {
  const { user, isLoading } = useAuthContext();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="flex items-center gap-2 text-slate-400 text-sm animate-fade-in">
          <span className="text-xl">🐾</span>
          <span>Loading…</span>
        </div>
      </div>
    );
  }

  if (user) return <ChatPage />;

  return <LandingPage />;
}
