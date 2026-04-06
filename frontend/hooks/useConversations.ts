"use client";

import { useCallback, useState } from "react";
import type { ConversationSummary } from "@/types/chat";
import { useAuthContext } from "@/components/AuthProvider";

export function useConversations() {
  const { token } = useAuthContext();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const authHeaders = token
    ? { Authorization: `Bearer ${token}` }
    : ({} as Record<string, string>);

  const fetchConversations = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const res = await fetch("/api/conversations", { headers: authHeaders });
      if (res.ok) setConversations(await res.json());
    } catch {
      // silent
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const loadConversation = useCallback(
    async (id: string) => {
      if (!token) return null;
      try {
        const res = await fetch(`/api/conversations/${id}`, {
          headers: authHeaders,
        });
        if (res.ok) return await res.json();
      } catch {
        // silent
      }
      return null;
    },
    [token],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      if (!token) return;
      try {
        await fetch(`/api/conversations/${id}`, {
          method: "DELETE",
          headers: authHeaders,
        });
        setConversations((prev) => prev.filter((c) => c.id !== id));
      } catch {
        // silent
      }
    },
    [token],
  );

  return {
    conversations,
    isLoading,
    fetchConversations,
    loadConversation,
    deleteConversation,
  };
}
