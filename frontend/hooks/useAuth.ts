"use client";

import { useCallback, useEffect, useState } from "react";
import type { User } from "@/types/chat";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = typeof window !== "undefined"
      ? localStorage.getItem("vetchat_token")
      : null;

    if (!stored) {
      setIsLoading(false);
      return;
    }

    setToken(stored);
    fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${stored}` },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setUser(data);
        } else {
          localStorage.removeItem("vetchat_token");
          setToken(null);
        }
      })
      .catch(() => {
        localStorage.removeItem("vetchat_token");
        setToken(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : {};
    if (!res.ok) throw new Error(data.detail || "Login failed");
    localStorage.setItem("vetchat_token", data.token);
    setToken(data.token);
    setUser({ id: data.user_id, email: data.email, full_name: data.full_name });
    return data;
  }, []);

  const register = useCallback(async (email: string) => {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : {};
    if (!res.ok) throw new Error(data.detail || "Registration failed");
    localStorage.setItem("vetchat_token", data.token);
    setToken(data.token);
    setUser({ id: data.user_id, email: data.email, full_name: data.full_name });
    return data;
  }, []);

  const logout = useCallback(() => {
    if (typeof window !== "undefined") localStorage.removeItem("vetchat_token");
    setToken(null);
    setUser(null);
  }, []);

  const updateProfile = useCallback(
    async (data: { full_name?: string; clinic?: string; country?: string }) => {
      const res = await fetch("/api/auth/profile", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });
      const text = await res.text();
      const updated = text ? JSON.parse(text) : {};
      if (!res.ok) throw new Error(updated.detail || "Update failed");
      setUser((prev) => (prev ? { ...prev, ...data } : prev));
    },
    [token],
  );

  return { user, token, isLoading, login, register, logout, updateProfile };
}
