"use client";

import { useState } from "react";

interface EmergencyBannerProps {
  resources: string[];
}

export default function EmergencyBanner({ resources }: EmergencyBannerProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 mb-3 animate-fade-in">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 text-left"
      >
        <span className="text-base">🚨</span>
        <span className="font-semibold text-red-800 text-sm flex-1">
          Emergency resources detected — tap to view
        </span>
        <span className="text-red-400 text-xs shrink-0">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {expanded && resources.length > 0 && (
        <ul className="mt-2 space-y-1 pl-6 border-t border-red-200 pt-2">
          {resources.map((r, i) => (
            <li key={i} className="text-red-800 text-xs">
              • {r}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
