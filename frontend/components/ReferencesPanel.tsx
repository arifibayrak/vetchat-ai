"use client";

import { useState } from "react";
import type { CitationItem, LiveResourceItem } from "@/types/chat";

interface ReferencesPanelProps {
  citations: CitationItem[];
  liveResources: LiveResourceItem[];
}

const SOURCE_BADGE: Record<string, string> = {
  "ScienceDirect": "bg-orange-100 text-orange-700",
  "Scopus":        "bg-orange-100 text-orange-700",
  "Springer Nature": "bg-green-100 text-green-700",
};

const DOC_TYPE_BADGE: Record<string, string> = {
  "Article":          "bg-blue-50 text-blue-700",
  "Review":           "bg-purple-50 text-purple-700",
  "Conference Paper": "bg-yellow-50 text-yellow-700",
  "Book Chapter":     "bg-indigo-50 text-indigo-700",
  "Editorial":        "bg-gray-100 text-gray-600",
  "Letter":           "bg-gray-100 text-gray-600",
};

/** Format: Vol. 42, No. 3, pp. 123–145 */
function formatLocator(volume?: string, issue?: string, pages?: string): string {
  const parts: string[] = [];
  if (volume) parts.push(`Vol. ${volume}`);
  if (issue)  parts.push(`No. ${issue}`);
  if (pages)  parts.push(`pp. ${pages}`);
  return parts.join(", ");
}

/** Full academic citation string */
function academicCitation(e: ReturnType<typeof buildEntries>[number]): string {
  const parts: string[] = [];
  if (e.authors) parts.push(`${e.authors}.`);
  parts.push(`(${e.year}).`);
  parts.push(`${e.title}.`);
  let journalPart = `*${e.journal}*`;
  const locator = formatLocator(e.volume, e.issue, e.pages);
  if (locator) journalPart += `, ${locator}`;
  parts.push(journalPart + ".");
  if (e.doi) parts.push(`https://doi.org/${e.doi}`);
  return parts.join(" ");
}

function buildEntries(citations: CitationItem[], liveResources: LiveResourceItem[]) {
  return citations.map((c, i) => {
    const lr = liveResources[i];
    return {
      ref:            c.ref,
      source:         lr?.source ?? "Literature",
      title:          c.title,
      journal:        c.journal,
      year:           c.year,
      authors:        c.authors,
      doi:            c.doi,
      url:            c.url || (c.doi ? `https://doi.org/${c.doi}` : ""),
      abstract:       c.abstract || lr?.abstract || "",
      relevant_quote: c.relevant_quote || "",
      volume:         c.volume || lr?.volume || "",
      issue:          c.issue  || lr?.issue  || "",
      pages:          c.pages  || lr?.pages  || "",
      doc_type:       c.doc_type || lr?.doc_type || "",
      cited_by:       c.cited_by ?? lr?.cited_by ?? 0,
    };
  });
}

export default function ReferencesPanel({ citations, liveResources }: ReferencesPanelProps) {
  const [open, setOpen] = useState(true);
  const [expandedAbstracts, setExpandedAbstracts] = useState<Record<number, boolean>>({});
  const [copiedRef, setCopiedRef] = useState<number | null>(null);

  if (citations.length === 0 && liveResources.length === 0) return null;

  const entries = buildEntries(citations, liveResources);

  const toggleAbstract = (ref: number) =>
    setExpandedAbstracts((prev) => ({ ...prev, [ref]: !prev[ref] }));

  const copyCitation = (e: (typeof entries)[number]) => {
    navigator.clipboard.writeText(academicCitation(e)).catch(() => {});
    setCopiedRef(e.ref);
    setTimeout(() => setCopiedRef(null), 2000);
  };

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
              {/* Badge row */}
              <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                <span className="shrink-0 w-5 h-5 rounded-full bg-violet-600 text-white text-xs font-bold flex items-center justify-center">
                  {e.ref}
                </span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SOURCE_BADGE[e.source] ?? "bg-gray-100 text-gray-600"}`}>
                  {e.source}
                </span>
                {e.doc_type && (
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${DOC_TYPE_BADGE[e.doc_type] ?? "bg-gray-100 text-gray-600"}`}>
                    {e.doc_type}
                  </span>
                )}
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
                  className="text-sm font-medium text-blue-700 hover:underline leading-snug block"
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
                    className="text-blue-500 hover:underline font-mono"
                  >
                    {e.doi}
                  </a>
                </p>
              )}

              {/* Copy citation button */}
              <button
                onClick={() => copyCitation(e)}
                className="mt-1.5 text-xs text-gray-400 hover:text-gray-700 transition-colors"
              >
                {copiedRef === e.ref ? "✓ Copied" : "Copy citation"}
              </button>

              {/* Relevant quote — always visible when present */}
              {e.relevant_quote && (
                <blockquote className="mt-2 border-l-4 border-amber-400 bg-amber-50 px-3 py-2 rounded-r-md">
                  <p className="text-xs text-amber-900 italic leading-relaxed">
                    📌 &ldquo;{e.relevant_quote}&rdquo;
                  </p>
                </blockquote>
              )}

              {/* Full abstract toggle */}
              {e.abstract && (
                <div className="mt-2">
                  <button
                    onClick={() => toggleAbstract(e.ref)}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium transition-colors"
                  >
                    {expandedAbstracts[e.ref] ? "Hide abstract" : "Show full abstract"}
                  </button>
                  {expandedAbstracts[e.ref] && (
                    <blockquote className="mt-1 border-l-4 border-violet-300 bg-violet-50 px-3 py-2 rounded-r-md">
                      <p className="text-xs text-violet-800 leading-relaxed italic">
                        {e.abstract.length > 600
                          ? e.abstract.slice(0, 600) + "…"
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
