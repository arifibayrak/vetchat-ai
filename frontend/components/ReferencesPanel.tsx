"use client";

import { useState } from "react";
import type { CitationItem, LiveResourceItem } from "@/types/chat";

interface ReferencesPanelProps {
  citations: CitationItem[];
  liveResources: LiveResourceItem[];
  totalSources?: number;
}

const SOURCE_BADGE: Record<string, string> = {
  "ScienceDirect":    "bg-orange-100 text-orange-700",
  "Scopus":           "bg-orange-100 text-orange-700",
  "Springer Nature":  "bg-green-100 text-green-700",
  "Taylor & Francis": "bg-teal-100 text-teal-700",
  "Literature":       "bg-slate-100 text-slate-600",
};

const RELEVANCE_STYLES: Record<string, { dot: string; label: string; text: string }> = {
  high:       { dot: "bg-emerald-500", label: "Directly relevant",   text: "text-emerald-700" },
  moderate:   { dot: "bg-amber-400",   label: "Related",             text: "text-amber-700"  },
  tangential: { dot: "bg-slate-400",   label: "Background context",  text: "text-slate-500"  },
};

function buildEntries(citations: CitationItem[], liveResources: LiveResourceItem[]) {
  return citations.map((c, i) => {
    const lr = liveResources[i];
    const source = c.source || lr?.source || "Literature";
    return {
      ref:            c.ref,
      source,
      publisher:      c.publisher || "",
      title:          c.title,
      journal:        c.journal,
      year:           c.year,
      authors:        c.authors,
      doi:            c.doi,
      url:            c.url || (c.doi ? `https://doi.org/${c.doi}` : ""),
      abstract:       c.abstract || lr?.abstract || "",
      relevant_quote: c.relevant_quote || "",
      intext_passage: c.intext_passage || "",
      volume:         c.volume || lr?.volume || "",
      issue:          c.issue  || lr?.issue  || "",
      pages:          c.pages  || lr?.pages  || "",
      doc_type:       c.doc_type || lr?.doc_type || "",
      cited_by:       c.cited_by ?? lr?.cited_by ?? 0,
      relevance:      c.relevance || "",
    };
  });
}

function RefCard({ e }: { e: ReturnType<typeof buildEntries>[number] }) {
  const [expanded, setExpanded] = useState(false);
  const hasExtra = !!(e.abstract || e.relevant_quote || e.intext_passage);

  const locator = [
    e.journal ? `${e.journal}` : "",
    e.volume ? `${e.volume}${e.issue ? `(${e.issue})` : ""}` : "",
    e.pages ? `pp. ${e.pages}` : "",
    e.year ? `${e.year}` : "",
  ].filter(Boolean).join(" · ");

  return (
    <li
      id={`citation-${e.ref}`}
      className="flex flex-col gap-1 bg-white border border-gray-100 rounded-lg px-3 py-2.5 scroll-mt-4 hover:border-teal-200 transition-colors"
    >
      {/* Top row: number + source badge + doc type + cited-by */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="shrink-0 w-5 h-5 rounded-full bg-violet-600 text-white text-[10px] font-bold flex items-center justify-center">
          {e.ref}
        </span>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${SOURCE_BADGE[e.source] ?? "bg-gray-100 text-gray-600"}`}>
          {e.source}
        </span>
        {e.doc_type && (
          <span className="text-[10px] text-gray-400">{e.doc_type}</span>
        )}
        {e.cited_by > 0 && (
          <span className="text-[10px] text-gray-400 ml-auto">cited {e.cited_by}×</span>
        )}
      </div>

      {/* Title */}
      {e.url ? (
        <a
          href={e.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-semibold text-teal-700 hover:underline leading-snug"
        >
          {e.title}
        </a>
      ) : (
        <span className="text-xs font-semibold text-gray-800 leading-snug">{e.title}</span>
      )}

      {/* Authors */}
      {e.authors && (
        <p className="text-[10px] text-gray-500 leading-snug truncate">{e.authors}</p>
      )}

      {/* Journal locator */}
      {locator && (
        <p className="text-[10px] text-gray-400 leading-snug italic">{locator}</p>
      )}

      {/* Relevance indicator */}
      {e.relevance && RELEVANCE_STYLES[e.relevance] && (
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className={`w-1.5 h-1.5 rounded-full ${RELEVANCE_STYLES[e.relevance].dot}`} />
          <span className={`text-[10px] font-medium ${RELEVANCE_STYLES[e.relevance].text}`}>
            {RELEVANCE_STYLES[e.relevance].label}
          </span>
        </div>
      )}

      {/* Expand toggle */}
      {hasExtra && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-[10px] text-teal-600 hover:text-teal-800 font-medium text-left mt-0.5 transition-colors"
        >
          {expanded ? "▲ less" : "▼ more"}
        </button>
      )}

      {expanded && (
        <div className="mt-1 space-y-2">
          {e.intext_passage && (
            <blockquote className="border-l-2 border-teal-300 bg-teal-50 px-2 py-1.5 rounded-r">
              <p className="text-[10px] text-teal-900 italic leading-relaxed">"{e.intext_passage}"</p>
            </blockquote>
          )}
          {e.relevant_quote && (
            <blockquote className="border-l-2 border-violet-300 bg-violet-50 px-2 py-1.5 rounded-r">
              <p className="text-[10px] text-violet-900 italic leading-relaxed">"{e.relevant_quote}"</p>
            </blockquote>
          )}
          {e.abstract && (
            <blockquote className="border-l-2 border-gray-200 bg-gray-50 px-2 py-1.5 rounded-r">
              <p className="text-[10px] text-gray-600 italic leading-relaxed">{e.abstract}</p>
            </blockquote>
          )}
          {e.doi && (
            <p className="text-[10px] text-gray-400">
              DOI:{" "}
              <a href={`https://doi.org/${e.doi}`} target="_blank" rel="noopener noreferrer" className="text-teal-600 hover:underline font-mono">
                {e.doi}
              </a>
            </p>
          )}
        </div>
      )}
    </li>
  );
}

export default function ReferencesPanel({ citations, liveResources, totalSources }: ReferencesPanelProps) {
  const [open, setOpen] = useState(true);

  if (citations.length === 0 && liveResources.length === 0) return null;

  const entries = buildEntries(citations, liveResources);
  const publishers = Array.from(new Set(entries.map((e) => e.publisher).filter(Boolean)));

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 text-sm font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
      >
        <span>
          📚 References ({entries.length}
          {totalSources && totalSources > entries.length ? ` cited of ${totalSources} retrieved` : ""})
        </span>
        <span className="text-gray-400 text-xs">{open ? "▲ hide" : "▼ show"}</span>
      </button>

      {open && (
        <>
          <div className="px-3 py-3 bg-white">
            <ol className="grid grid-cols-1 sm:grid-cols-2 gap-2 list-none m-0 p-0">
              {entries.map((e) => (
                <RefCard key={e.ref} e={e} />
              ))}
            </ol>
          </div>

          <div className="px-4 py-2 bg-slate-50 border-t border-gray-100 flex items-start gap-2">
            <span className="text-teal-600 text-sm shrink-0 mt-0.5">🔒</span>
            <p className="text-xs text-slate-500 leading-relaxed">
              <span className="font-semibold text-slate-700">Source integrity: </span>
              Grounded exclusively in peer-reviewed veterinary literature
              {publishers.length > 0 && <> ({publishers.join(", ")})</>}.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
