"use client";

import { useState } from "react";
import type { LiveResourceItem } from "@/types/chat";

const SOURCE_BADGE: Record<string, string> = {
  "ScienceDirect": "bg-orange-100 text-orange-700",
  "Springer Nature": "bg-green-100 text-green-700",
};

interface LiveResourcesPanelProps {
  resources: LiveResourceItem[];
}

export default function LiveResourcesPanel({ resources }: LiveResourcesPanelProps) {
  const [open, setOpen] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  if (resources.length === 0) return null;

  return (
    <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2 text-sm font-semibold text-blue-800 hover:bg-blue-100 transition-colors"
      >
        <span>📚 Live Literature ({resources.length} results)</span>
        <span className="text-blue-500">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <ul className="divide-y divide-blue-100">
          {resources.map((r, i) => (
            <li key={i} className="px-4 py-3 bg-white hover:bg-blue-50 transition-colors">
              <div className="flex items-start gap-2">
                {/* Source badge */}
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${SOURCE_BADGE[r.source] ?? "bg-gray-100 text-gray-600"}`}>
                  {r.source}
                </span>

                <div className="flex-1 min-w-0">
                  {/* Title + link */}
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-gray-800 hover:text-blue-700 hover:underline line-clamp-2"
                  >
                    {r.title}
                  </a>

                  {/* Meta */}
                  <p className="text-xs text-gray-500 mt-0.5">
                    {r.authors && <span>{r.authors} · </span>}
                    <em>{r.journal}</em>
                    {r.year ? ` · ${r.year}` : ""}
                  </p>

                  {/* Abstract toggle */}
                  {r.abstract && (
                    <>
                      <button
                        onClick={() => setExpanded(expanded === i ? null : i)}
                        className="text-xs text-blue-500 hover:underline mt-1"
                      >
                        {expanded === i ? "Hide abstract" : "Show abstract"}
                      </button>
                      {expanded === i && (
                        <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                          {r.abstract.length > 400
                            ? r.abstract.slice(0, 400) + "…"
                            : r.abstract}
                        </p>
                      )}
                    </>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
