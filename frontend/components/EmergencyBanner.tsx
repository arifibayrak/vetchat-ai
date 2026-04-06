"use client";

interface EmergencyBannerProps {
  resources: string[];
}

export default function EmergencyBanner({ resources }: EmergencyBannerProps) {
  return (
    <div className="rounded-lg border-2 border-red-600 bg-red-50 p-4">
      <div className="flex items-start gap-3">
        <span className="text-2xl">🚨</span>
        <div>
          <p className="font-bold text-red-800 text-lg">EMERGENCY CLINICAL ALERT</p>
          <p className="text-red-700 mt-1 text-sm">
            Activate emergency clinical protocol immediately. Stabilise patient and contact a veterinary toxicologist or emergency specialist as indicated.
          </p>
          {resources.length > 0 && (
            <ul className="mt-3 space-y-1">
              {resources.map((r, i) => (
                <li key={i} className="text-red-800 text-sm font-medium">
                  • {r}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
