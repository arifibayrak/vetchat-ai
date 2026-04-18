"use client";

import type { EmergencyPreliminary } from "@/types/chat";

interface Props {
  card: EmergencyPreliminary;
}

export default function EmergencyPreliminaryCard({ card }: Props) {
  return (
    <div className="rounded-lg border-2 border-red-400 bg-red-50 px-4 py-3 mb-4 animate-fade-in">
      <div className="flex items-center gap-2 mb-2.5">
        <span className="text-base" aria-hidden>🚨</span>
        <h3 className="font-bold text-red-900 text-sm leading-snug">{card.heading}</h3>
      </div>
      <ol className="space-y-1.5 pl-0.5">
        {card.priorities.map((priority, i) => (
          <li key={i} className="flex gap-2 text-red-800 text-xs leading-relaxed">
            <span className="font-bold shrink-0 text-red-500 w-4">{i + 1}.</span>
            <span>{priority}</span>
          </li>
        ))}
      </ol>
      <p className="text-xs text-red-400 mt-2.5 italic">
        Full evidence synthesis loading below…
      </p>
    </div>
  );
}
