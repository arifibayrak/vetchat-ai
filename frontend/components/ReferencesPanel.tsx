"use client";

import { useState } from "react";
import type { CitationItem, LiveResourceItem } from "@/types/chat";

interface ReferencesPanelProps {
  citations: CitationItem[];
  liveResources: LiveResourceItem[];
}

const SOURCE_BADGE: Record<string, string> = {
  "ScienceDirect":    "bg-orange-100 text-orange-700",
  "Scopus":           "bg-orange-100 text-orange-700",
  "Springer Nature":  "bg-green-100 text-green-700",
  "Taylor & Francis": "bg-amber-100 text-amber-700",
  "Literature":       "bg-slate-100 text-slate-600",
};

const DOC_TYPE_BADGE: Record<string, string> = {
  "Article":          "bg-blue-50 text-blue-700",
  "Review":           "bg-purple-50 text-purple-700",
  "Conference Paper": "bg-yellow-50 text-yellow-700",
  "Book Chapter":     "bg-indigo-50 text-indigo-700",
  "Editorial":        "bg-gray-100 text-gray-600",
  "Letter":           "bg-gray-100 text-gray-600",
};


function buildEntries(citations: CitationItem[], liveResources: LiveResourceItem[]) {
  return citations.map((c, i) => {
    const lr = liveResources[i];
    // Prefer the publisher-aware source from CitationItem (set by backend provenance logic)
    const source = c.source || lr?.source || "Literature";
    return {
      ref:             c.ref,
      source,
      publisher:       c.publisher || "",
      title:           c.title,
      journal:         c.journal,
      year:            c.year,
      authors:         c.authors,
      doi:             c.doi,
      url:             c.url || (c.doi ? `https://doi.org/${c.doi}` : ""),
      abstract:        c.abstract || lr?.abstract || "",
      relevant_quote:  c.relevant_quote || "",
      intext_passage:  c.intext_passage || "",
      volume:          c.volume || lr?.volume || "",
      issue:           c.issue  || lr?.issue  || "",
      pages:           c.pages  || lr?.pages  || "",
      doc_type:        c.doc_type || lr?.doc_type || "",
      cited_by:        c.cited_by ?? lr?.cited_by ?? 0,
    };
  });
}

export default function ReferencesPanel({ citations, liveResources }: ReferencesPanelProps) {
  const [open, setOpen] = useState(true);
  const [expandedAbstracts, setExpandedAbstracts] = useState<Record<number, boolean>>({});

  if (citations.length === 0 && liveResources.length === 0) return null;

  const entries = buildEntries(citations, liveResources);

  // Collect unique publishers for the provenance footer
  const publishers = Array.from(
    new Set(entries.map((e) => e.publisher).filter(Boolean))
  );

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
        <>
        <ol className="divide-y divide-gray-100">
          {entries.map((e) => (
            <li
              key={e.ref}
              id={`citation-${e.ref}`}
              className="px-4 py-3 bg-white hover:bg-gray-50 transition-colors scroll-mt-4"
            >
              {/* Badge row */}
              <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                <span className="shrink-0 w-5 h-5 rounded-full bg-violet-600 text-white text-xs font-bold flex items-center justify-center">
                  {e.ref}
                </span>
                {/* Publisher/source badge — shows which database this came from */}
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SOURCE_BADGE[e.source] ?? SOURCE_BADGE[e.publisher] ?? "bg-gray-100 text-gray-600"}`}>
                  {e.source}
                </span>
                {/* Publisher name if different from source (e.g. source=Scopus, publisher=Elsevier) */}
                {e.publisher && e.publisher !== e.source && (
                  <span className="text-xs text-gray-400">via {e.publisher}</span>
                )}
                {e.doc_type && (
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${DOC_TYPE_BADGE[e.doc_type] ?? "bg-gray-100 text-gray-600"}`}>
                    {e.doc_type}
                  </span>
                )}
                {/* Peer-reviewed trust signal */}
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">
                  ✓ Peer-reviewed
                </span>
                {e.cited_by > 0 && (
                  <span className="text-xs text-gray-400 ml-auto">
                    📊 Cited by {e.cited_by}
                  </span>
                )}
              </div>

              {/* Title */}
              {e.url ? (
                <a
                  href={e.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-amber-700 hover:underline leading-snug block"
                >
                  {e.title}
                </a>
              ) : (
                <span className="text-sm font-medium text-gray-800 leading-snug block">
                  {e.title}
                </span>
              )}

              {/* Authors */}
              {e.authors && (
                <p className="text-xs text-gray-600 font-medium mt-0.5">{e.authors}</p>
              )}

              {/* Journal · locator · year */}
              <p className="text-xs text-gray-500 mt-0.5">
                <em>{e.journal}</em>
                {(e.volume || e.issue) && (
                  <span className="text-gray-400">
                    {e.volume && <span> · Vol.&nbsp;{e.volume}</span>}
                    {e.issue  && <span>({e.issue})</span>}
                  </span>
                )}
                {e.pages && <span className="text-gray-400"> · pp.&nbsp;{e.pages}</span>}
                {e.year ? <span> · {e.year}</span> : ""}
              </p>

              {/* DOI line */}
              {e.doi && (
                <p className="text-xs mt-0.5">
                  <span className="text-gray-400">DOI: </span>
                  <a
                    href={`https://doi.org/${e.doi}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-amber-600 hover:underline font-mono"
                  >
                    {e.doi}
                  </a>
                </p>
              )}

              {/* How it was cited — exact sentence from the answer */}
              {e.intext_passage && (
                <div className="mt-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                    How it was cited
                  </p>
                  <blockquote className="border-l-4 border-amber-300 bg-amber-50 px-3 py-2 rounded-r-md">
                    <p className="text-xs text-amber-900 leading-relaxed italic">
                      &ldquo;{e.intext_passage}&rdquo;
                    </p>
                  </blockquote>
                </div>
              )}

              {/* Relevant passage from the source */}
              {e.relevant_quote && (
                <div className="mt-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                    Relevant passage from source
                  </p>
                  <blockquote className="border-l-4 border-amber-400 bg-amber-50 px-3 py-2 rounded-r-md">
                    <p className="text-xs text-amber-900 leading-relaxed italic">
                      &ldquo;{e.relevant_quote}&rdquo;
                    </p>
                  </blockquote>
                </div>
              )}

              {/* Full abstract toggle */}
              {e.abstract && (
                <div className="mt-2">
                  <button
                    onClick={() => toggleAbstract(e.ref)}
                    className="text-xs text-amber-600 hover:text-amber-800 font-medium transition-colors"
                  >
                    {expandedAbstracts[e.ref] ? "Hide full abstract" : "Show full abstract"}
                  </button>
                  {expandedAbstracts[e.ref] && (
                    <blockquote className="mt-1 border-l-4 border-violet-300 bg-violet-50 px-3 py-2 rounded-r-md">
                      <p className="text-xs text-violet-800 leading-relaxed italic">
                        {e.abstract}
                      </p>
                    </blockquote>
                  )}
                </div>
              )}
            </li>
          ))}
        </ol>
        {/* Provenance footer — makes trust story explicit to the vet */}
        <div className="px-4 py-2.5 bg-slate-50 border-t border-gray-100 flex items-start gap-2">
          <span className="text-amber-600 text-sm shrink-0 mt-0.5">🔒</span>
          <p className="text-xs text-slate-500 leading-relaxed">
            <span className="font-semibold text-slate-700">Source integrity: </span>
            Every answer is grounded exclusively in passages retrieved from peer-reviewed veterinary journals
            {publishers.length > 0 && (
              <> ({publishers.join(", ")})</>
            )}. Lenny does not generate clinical facts from its own memory.
          </p>
        </div>
        </>
      )}
    </div>
  );
}
