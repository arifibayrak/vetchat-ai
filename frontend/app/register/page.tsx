"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { useAuthContext } from "@/components/AuthProvider";

const COUNTRIES = [
  "Australia", "Canada", "France", "Germany", "Ireland", "Netherlands",
  "New Zealand", "South Africa", "Spain", "Sweden", "Turkey",
  "United Kingdom", "United States", "Other",
];

export default function RegisterPage() {
  const { register } = useAuthContext();
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

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(
        form.email,
        form.password,
        form.full_name,
        form.clinic,
        form.country,
      );
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const field = (
    label: string,
    name: keyof typeof form,
    type = "text",
    required = true,
    placeholder = "",
  ) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {!required && (
          <span className="text-gray-400 font-normal ml-1">(optional)</span>
        )}
      </label>
      <input
        type={type}
        value={form[name]}
        onChange={set(name)}
        required={required}
        placeholder={placeholder}
        autoComplete={type === "password" ? "new-password" : undefined}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <p className="text-4xl mb-2">🐾</p>
          <h1 className="text-2xl font-bold text-gray-800">Create your account</h1>
          <p className="text-sm text-gray-500 mt-1">
            Evidence-based clinical reference for veterinary professionals
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {field("Full name", "full_name")}
          {field("Email", "email", "email")}
          {field("Password", "password", "password")}
          {field("Clinic / institution", "clinic", "text", false)}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Country
            </label>
            <select
              value={form.country}
              onChange={set("country")}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="">Select country…</option>
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Already have an account?{" "}
          <Link href="/login" className="text-blue-600 hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
