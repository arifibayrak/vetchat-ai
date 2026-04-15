"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useAuthContext } from "@/components/AuthProvider";

export default function SignOutPage() {
  const { logout } = useAuthContext();

  // Ensure token is cleared if user lands here directly
  useEffect(() => {
    logout();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-10 w-full max-w-md text-center animate-slide-up">
        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center mx-auto mb-6 shadow-md">
          <span className="text-3xl">🐾</span>
        </div>

        {/* Message */}
        <h1 className="text-2xl font-bold text-slate-900 mb-2">You&apos;ve been signed out</h1>
        <p className="text-sm text-slate-500 mb-8">
          Thanks for using Lenny. Your session has been ended securely.
        </p>

        {/* Actions */}
        <div className="flex flex-col gap-3">
          <Link
            href="/login"
            className="w-full py-3 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-xl text-sm transition-colors shadow-sm"
          >
            Sign back in
          </Link>
          <Link
            href="/"
            className="w-full py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-xl text-sm transition-colors"
          >
            Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
