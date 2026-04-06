"use client";

import { useState } from "react";
import type { CitationItem } from "@/types/chat";

interface CitationPanelProps {
  citations: CitationItem[];
}

export default function CitationPanel({ citations }: CitationPanelProps) {
  const [open, setOpen] = useState(true);

  if (citations.length === 0) return null;

  return (
    <div className="mt-4 rounded-xl border border-violet-200 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2 bg-violet-50 text-sm font-semibold text-violet-800 hover:bg-violet-100 transition-colors"
      >
        <span>🔗 References ({citations.length})</span>
        <span className="text-violet-400 text-xs">{open ? "▲ hide" : "▼ show"}</span>
      </button>

      {open && (
        <ol className="divide-y divide-violet-100">
          {citations.map((c) => {
            const doiUrl = c.url || (c.doi ? `https://doi.org/${c.doi}` : null);

            return (
              <li key={c.ref} id={`citation-${c.ref}`} className="flex gap-3 px-4 py-3 bg-white hover:bg-violet-50 transition-colors scroll-mt-4">
                {/* Ref badge */}
                <span className="shrink-0 w-6 h-6 rounded-full bg-violet-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                  {c.ref}
                </span>

                <div className="flex-1 min-w-0">
                  {/* Title as link */}
                  {doiUrl ? (
                    <a
                      href={doiUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-violet-700 hover:text-violet-900 hover:underline leading-snug block"
                    >
                      {c.title}
                    </a>
                  ) : (
                    <span className="text-sm font-medium text-gray-800 leading-snug block">{c.title}</span>
                  )}

                  {/* Authors + journal + year */}
                  <p className="text-xs text-gray-500 mt-0.5">
                    {c.authors && <span className="font-medium text-gray-600">{c.authors}</span>}
                    {c.authors && " · "}
                    <em>{c.journal}</em>
                    {c.year ? ` · ${c.year}` : ""}
                  </p>

                  {/* DOI as explicit link */}
                  {doiUrl && (
                    <a
                      href={doiUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-500 hover:underline mt-0.5 block font-mono"
                    >
                      {doiUrl}
                    </a>
                  )}

                  {/* Abstract quote block */}
                  {c.abstract && (
                    <blockquote className="mt-2 border-l-4 border-violet-300 bg-violet-50 px-3 py-2 rounded-r-md">
                      <p className="text-xs text-violet-800 leading-relaxed italic">
                        {c.abstract.length > 450
                          ? c.abstract.slice(0, 450) + "…"
                          : c.abstract}
                      </p>
                    </blockquote>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
