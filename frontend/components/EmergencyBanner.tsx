"use client";

export default function EmergencyBanner() {
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 mb-3 flex items-center gap-2 animate-fade-in">
      <span className="text-base" aria-hidden>🚨</span>
      <span className="font-semibold text-red-800 text-sm">
        Emergency query detected — immediate actions shown above
      </span>
    </div>
  );
}
