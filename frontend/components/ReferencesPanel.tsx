"use client";

import { useState } from "react";
import type { CitationItem, LiveResourceItem } from "@/types/chat";

interface ReferencesPanelProps {
  citations: CitationItem[];
  liveResources: LiveResourceItem[];
}

const SOURCE_BADGE: Record<string, string> = {
  "ScienceDirect": "bg-orange-100 text-orange-700",
  "Scopus": "bg-orange-100 text-orange-700",
  "Springer Nature": "bg-green-100 text-green-700",
};

export default function ReferencesPanel({ citations, liveResources }: ReferencesPanelProps) {
  const [open, setOpen] = useState(true);
  const [expandedAbstracts, setExpandedAbstracts] = useState<Record<number, boolean>>({});

  if (citations.length === 0 && liveResources.length === 0) return null;

  // Merge citations (numbered, with abstract) + live resources (source badge)
  const entries = citations.map((c, i) => ({
    ref: c.ref,
    source: liveResources[i]?.source ?? "Literature",
    title: c.title,
    journal: c.journal,
    year: c.year,
    authors: c.authors,
    doi: c.doi,
    url: c.url || (c.doi ? `https://doi.org/${c.doi}` : ""),
    abstract: c.abstract || liveResources[i]?.abstract || "",
  }));

  const toggleAbstract = (ref: number) =>
    setExpandedAbstracts((prev) => ({ ...prev, [ref]: !prev[ref] }));

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 text-sm font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
      >
        <span>📚 References ({entries.length})</span>
        <span className="text-gray-400 text-xs">{open ? "▲ hide" : "▼ show"}</span>
      </button>

      {open && (
        <ol className="divide-y divide-gray-100">
          {entries.map((e) => (
            <li
              key={e.ref}
              id={`citation-${e.ref}`}
              className="px-4 py-3 bg-white hover:bg-gray-50 transition-colors scroll-mt-4"
            >
              <div className="flex items-start gap-2 mb-1">
                {/* Ref badge */}
                <span className="shrink-0 w-5 h-5 rounded-full bg-violet-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                  {e.ref}
                </span>
                {/* Source badge */}
                <span
                  className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
                    SOURCE_BADGE[e.source] ?? "bg-gray-100 text-gray-600"
                  }`}
                >
                  {e.source}
                </span>
              </div>

              {/* Title */}
              {e.url ? (
                <a
                  href={e.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-blue-700 hover:underline leading-snug block mt-1"
                >
                  {e.title}
                </a>
              ) : (
                <span className="text-sm font-medium text-gray-800 leading-snug block mt-1">
                  {e.title}
                </span>
              )}

              {/* Metadata */}
              <p className="text-xs text-gray-500 mt-0.5">
                {e.authors && (
                  <span className="font-medium text-gray-600">{e.authors}</span>
                )}
                {e.authors && " · "}
                <em>{e.journal}</em>
                {e.year ? ` · ${e.year}` : ""}
              </p>

              {/* Abstract toggle */}
              {e.abstract && (
                <div className="mt-2">
                  <button
                    onClick={() => toggleAbstract(e.ref)}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                  >
                    {expandedAbstracts[e.ref] ? "Hide abstract" : "Show abstract"}
                  </button>
                  {expandedAbstracts[e.ref] && (
                    <blockquote className="mt-1 border-l-4 border-violet-300 bg-violet-50 px-3 py-2 rounded-r-md">
                      <p className="text-xs text-violet-800 leading-relaxed italic">
                        {e.abstract.length > 500
                          ? e.abstract.slice(0, 500) + "…"
                          : e.abstract}
                      </p>
                    </blockquote>
                  )}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
