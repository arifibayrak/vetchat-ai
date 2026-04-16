"use client";

import Link from "next/link";
import { useEffect } from "react";

interface AuthGateModalProps {
  query: string | null;
  onClose: () => void;
}

export default function AuthGateModal({ query, onClose }: AuthGateModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full animate-scale-in"
      >
        <div className="text-center space-y-4">
          <span className="text-4xl block">🐾</span>

          <div>
            <h2 id="auth-modal-title" className="text-xl font-bold text-gray-800">
              Sign in to search veterinary literature
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Access peer-reviewed evidence from ScienceDirect, Springer Nature &amp; Taylor &amp; Francis
            </p>
          </div>

          {query && (
            <div className="bg-teal-50 border border-teal-200 rounded-lg px-4 py-3 text-sm text-teal-800 text-left">
              <span className="font-medium">Your question:</span>{" "}
              <span className="italic">&ldquo;{query}&rdquo;</span>
              <p className="text-xs text-teal-600 mt-1">Sign in to continue with this search</p>
            </div>
          )}

          <div className="flex flex-col gap-3 pt-2">
            <Link
              href="/register"
              className="w-full bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-xl py-3 text-sm transition-colors text-center"
            >
              Create free account
            </Link>
            <Link
              href="/login"
              className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold rounded-xl py-3 text-sm transition-colors text-center"
            >
              Sign in
            </Link>
          </div>

          <p className="text-xs text-gray-400 mt-1">
            Free during beta — no credit card required
          </p>

          <button
            onClick={onClose}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}
