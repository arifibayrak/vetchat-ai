"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { useAuthContext } from "@/components/AuthProvider";
import DogLogo from "@/components/DogLogo";

const COUNTRIES = [
  "Australia", "Canada", "France", "Germany", "Ireland", "Netherlands",
  "New Zealand", "South Africa", "Spain", "Sweden", "Turkey",
  "United Kingdom", "United States", "Other",
];

export default function RegisterPage() {
  const { user, register } = useAuthContext();
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    clinic: "",
    country: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Redirect already-authenticated users to the app
  useEffect(() => {
    if (user) router.replace("/");
  }, [user, router]);

  const set =
    (field: string) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(form.email, form.password, form.full_name, form.clinic, form.country);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4 py-8">
      {/* Back link */}
      <div className="w-full max-w-md mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-teal-600 transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Back to home
        </Link>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 w-full max-w-md animate-slide-up">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <DogLogo size={52} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
          <p className="text-sm text-slate-500 mt-1">
            Free during beta — no credit card required
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Full name */}
          <div>
            <label htmlFor="reg-name" className="block text-sm font-medium text-slate-700 mb-1.5">
              Full name <span className="text-red-500" aria-hidden="true">*</span>
            </label>
            <input
              id="reg-name"
              type="text"
              value={form.full_name}
              onChange={set("full_name")}
              required
              placeholder="Dr. Jane Smith"
              className="w-full border border-slate-300 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-shadow"
            />
          </div>

          {/* Email */}
          <div>
            <label htmlFor="reg-email" className="block text-sm font-medium text-slate-700 mb-1.5">
              Email <span className="text-red-500" aria-hidden="true">*</span>
            </label>
            <input
              id="reg-email"
              type="email"
              value={form.email}
              onChange={set("email")}
              required
              placeholder="you@clinic.com"
              className="w-full border border-slate-300 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-shadow"
            />
          </div>

          {/* Password */}
          <div>
            <label htmlFor="reg-password" className="block text-sm font-medium text-slate-700 mb-1.5">
              Password <span className="text-red-500" aria-hidden="true">*</span>
            </label>
            <input
              id="reg-password"
              type="password"
              value={form.password}
              onChange={set("password")}
              required
              placeholder="••••••••"
              autoComplete="new-password"
              className="w-full border border-slate-300 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-shadow"
            />
          </div>

          {/* Clinic (optional) */}
          <div>
            <label htmlFor="reg-clinic" className="block text-sm font-medium text-slate-700 mb-1.5">
              Clinic / institution{" "}
              <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <input
              id="reg-clinic"
              type="text"
              value={form.clinic}
              onChange={set("clinic")}
              placeholder="City Vet Clinic"
              className="w-full border border-slate-300 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-shadow"
            />
          </div>

          {/* Country */}
          <div>
            <label htmlFor="reg-country" className="block text-sm font-medium text-slate-700 mb-1.5">
              Country <span className="text-red-500" aria-hidden="true">*</span>
            </label>
            <select
              id="reg-country"
              value={form.country}
              onChange={set("country")}
              required
              className="w-full border border-slate-300 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent bg-white transition-shadow"
            >
              <option value="">Select country…</option>
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <svg className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white rounded-lg py-2.5 text-sm font-semibold transition-colors shadow-sm mt-2"
          >
            <span className="flex items-center justify-center gap-2">
              {loading && (
                <svg className="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
              Create free account
            </span>
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-teal-600 hover:text-teal-700 font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
