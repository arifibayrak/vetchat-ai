"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { useAuthContext } from "@/components/AuthProvider";

const COUNTRIES = [
  "Australia", "Canada", "France", "Germany", "Ireland", "Netherlands",
  "New Zealand", "South Africa", "Spain", "Sweden", "Turkey",
  "United Kingdom", "United States", "Other",
];

export default function ProfilePage() {
  const { user, isLoading, updateProfile } = useAuthContext();
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [clinic, setClinic] = useState("");
  const [country, setCountry] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
    if (user) {
      setFullName(user.full_name ?? "");
      setClinic(user.clinic ?? "");
      setCountry(user.country ?? "");
    }
  }, [user, isLoading, router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSaved(false);
    setSaving(true);
    try {
      await updateProfile({ full_name: fullName, clinic, country });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  };

  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400 text-sm animate-fade-in">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 w-full max-w-md animate-slide-up">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link
            href="/"
            className="text-gray-400 hover:text-gray-700 transition-colors text-sm"
          >
            ← Back to chat
          </Link>
        </div>

        <div className="text-center mb-6">
          <span className="text-4xl block mb-2">🐾</span>
          <h1 className="text-xl font-bold text-gray-800">Your Profile</h1>
          <p className="text-sm text-gray-500 mt-1">Manage your account information</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email — read only */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={user.email}
              readOnly
              className="w-full border border-gray-200 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-500 cursor-not-allowed"
            />
          </div>

          {/* Full name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            />
          </div>

          {/* Clinic */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Clinic / Practice{" "}
              <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={clinic}
              onChange={(e) => setClinic(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            />
          </div>

          {/* Country */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Country
            </label>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors bg-white"
            >
              <option value="">Select country…</option>
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-sm text-red-600 animate-fade-in">{error}</p>
          )}

          {saved && (
            <p className="text-sm text-green-600 animate-fade-in">
              ✓ Profile updated successfully
            </p>
          )}

          <button
            type="submit"
            disabled={saving}
            className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </form>
      </div>
    </div>
  );
}
