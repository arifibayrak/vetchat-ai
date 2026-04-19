"use client";

import { useState } from "react";
import type { CitationItem, EvidenceCounts, EvidenceTier, LiveResourceItem } from "@/types/chat";

interface ReferencesPanelProps {
  citations: CitationItem[];
  liveResources: LiveResourceItem[];
  totalSources?: number;
  hiddenReferences?: CitationItem[];
  evidenceCounts?: EvidenceCounts;
}

const SOURCE_BADGE: Record<string, string> = {
  "ScienceDirect":    "bg-orange-50 text-orange-700 ring-1 ring-orange-200",
  "Scopus":           "bg-orange-50 text-orange-700 ring-1 ring-orange-200",
  "Springer Nature":  "bg-green-50  text-green-700  ring-1 ring-green-200",
  "Taylor & Francis": "bg-teal-50   text-teal-700   ring-1 ring-teal-200",
  "Literature":       "bg-slate-50  text-slate-600  ring-1 ring-slate-200",
};

const TIER_STYLES: Record<EvidenceTier, { label: string; dot: string; text: string; bg: string }> = {
  direct:    { label: "Direct evidence",     dot: "bg-emerald-500", text: "text-emerald-800", bg: "bg-emerald-50 ring-emerald-200" },
  review:    { label: "Review",              dot: "bg-sky-500",     text: "text-sky-800",     bg: "bg-sky-50 ring-sky-200" },
  guideline: { label: "Guideline / Consensus", dot: "bg-violet-500", text: "text-violet-800",  bg: "bg-violet-50 ring-violet-200" },
  weak:      { label: "Weak indirect",       dot: "bg-amber-400",   text: "text-amber-800",   bg: "bg-amber-50 ring-amber-200" },
  none:      { label: "No direct evidence",  dot: "bg-slate-400",   text: "text-slate-600",   bg: "bg-slate-50 ring-slate-200" },
  "":        { label: "Relevant",            dot: "bg-slate-400",   text: "text-slate-600",   bg: "bg-slate-50 ring-slate-200" },
};

type Entry = ReturnType<typeof buildEntries>[number];

function buildEntries(citations: CitationItem[], liveResources: LiveResourceItem[]) {
  return citations.map((c, i) => {
    const lr = liveResources[i];
    return {
      ref:              c.ref,
      source:           c.source || lr?.source || "Literature",
      publisher:        c.publisher || "",
      title:            c.title,
      journal:          c.journal,
      year:             c.year,
      authors:          c.authors,
      doi:              c.doi,
      url:              c.url || (c.doi ? `https://doi.org/${c.doi}` : ""),
      abstract:         c.abstract || lr?.abstract || "",
      relevantQuote:    c.relevant_quote || "",
      intextPassage:    c.intext_passage || "",
      volume:           c.volume || lr?.volume || "",
      issue:            c.issue  || lr?.issue  || "",
      pages:            c.pages  || lr?.pages  || "",
      docType:          c.doc_type || lr?.doc_type || "",
      citedBy:          c.cited_by ?? lr?.cited_by ?? 0,
      relevance:        c.relevance || "",
      studyType:        c.study_type || "",
      speciesRelevance: c.species_relevance || "",
      whyItMatters:     c.why_it_matters || "",
      evidenceTier:     (c.evidence_tier ?? "") as EvidenceTier,
    };
  });
}

function formatAuthors(authors: string): string {
  if (!authors) return "";
  // Arlo stores authors as "Smith J, Jones K, Brown L" — compress to et al. past 2
  const parts = authors.split(/,\s*/).filter(Boolean);
  if (parts.length <= 2) return parts.join(", ");
  return `${parts[0]} et al.`;
}

function RefCard({ e }: { e: Entry }) {
  const [expanded, setExpanded] = useState(false);
  const hasExtra = !!(e.abstract || e.relevantQuote || e.intextPassage || e.doi);
  const tier = TIER_STYLES[e.evidenceTier] ?? TIER_STYLES[""];

  return (
    <li
      id={`citation-${e.ref}`}
      className="flex flex-col gap-1.5 bg-white border border-gray-200 rounded-xl px-3.5 py-3 scroll-mt-4 hover:border-teal-300 hover:shadow-sm transition-all"
    >
      {/* Top strip: ref number + evidence tier + source badge */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="shrink-0 w-6 h-6 rounded-full bg-violet-600 text-white text-[11px] font-bold flex items-center justify-center">
          {e.ref}
        </span>
        <span
          className={`text-[10px] font-medium px-2 py-0.5 rounded-full inline-flex items-center gap-1 ring-1 ${tier.bg} ${tier.text}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${tier.dot}`} aria-hidden />
          {tier.label}
        </span>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${SOURCE_BADGE[e.source] ?? "bg-gray-100 text-gray-600 ring-1 ring-gray-200"}`}>
          {e.source}
        </span>
        {e.citedBy > 0 && (
          <span className="text-[10px] text-gray-400 ml-auto tabular-nums">cited {e.citedBy}×</span>
        )}
      </div>

      {/* Title as primary heading */}
      {e.url ? (
        <a
          href={e.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold text-gray-900 hover:text-teal-700 hover:underline leading-snug"
        >
          {e.title}
        </a>
      ) : (
        <span className="text-sm font-semibold text-gray-900 leading-snug">{e.title}</span>
      )}

      {/* Clinician metadata row: Journal · Year · Study type · Species */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-gray-600 leading-tight">
        {e.journal && <span className="italic">{e.journal}</span>}
        {e.year > 0 && <><span className="text-gray-300">·</span><span className="tabular-nums">{e.year}</span></>}
        {e.studyType && (
          <>
            <span className="text-gray-300">·</span>
            <span className="font-medium text-gray-700">{e.studyType}</span>
          </>
        )}
        {e.speciesRelevance && (
          <>
            <span className="text-gray-300">·</span>
            <span className="text-gray-700">{e.speciesRelevance}</span>
          </>
        )}
      </div>

      {/* Compact authors line */}
      {e.authors && (
        <p className="text-[10px] text-gray-400 leading-tight truncate">{formatAuthors(e.authors)}</p>
      )}

      {/* Why it matters — the clinician-first value line */}
      {e.whyItMatters && (
        <p className="text-[11.5px] text-gray-700 leading-snug mt-0.5">
          <span className="font-medium text-teal-700">Why it matters: </span>
          {e.whyItMatters}
        </p>
      )}

      {/* Expand toggle (DOI, full abstract, and quote hidden by default) */}
      {hasExtra && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-[10px] text-teal-600 hover:text-teal-800 font-medium text-left mt-0.5 transition-colors"
          aria-expanded={expanded}
        >
          {expanded ? "▲ hide details" : "▼ details (quote · DOI · abstract)"}
        </button>
      )}

      {expanded && (
        <div className="mt-1 space-y-2">
          {e.intextPassage && (
            <blockquote className="border-l-2 border-teal-300 bg-teal-50 px-2 py-1.5 rounded-r">
              <p className="text-[10.5px] text-teal-900 italic leading-relaxed">"{e.intextPassage}"</p>
              <p className="text-[9px] text-teal-700 mt-0.5 uppercase tracking-wide">Cited in this answer</p>
            </blockquote>
          )}
          {e.relevantQuote && (
            <blockquote className="border-l-2 border-violet-300 bg-violet-50 px-2 py-1.5 rounded-r">
              <p className="text-[10.5px] text-violet-900 italic leading-relaxed">"{e.relevantQuote}"</p>
              <p className="text-[9px] text-violet-700 mt-0.5 uppercase tracking-wide">From the source abstract</p>
            </blockquote>
          )}
          {e.abstract && !e.relevantQuote && (
            <blockquote className="border-l-2 border-gray-200 bg-gray-50 px-2 py-1.5 rounded-r">
              <p className="text-[10.5px] text-gray-600 italic leading-relaxed">{e.abstract}</p>
            </blockquote>
          )}
          {(e.volume || e.pages || e.docType) && (
            <p className="text-[10px] text-gray-500">
              {[
                e.docType,
                e.volume ? `Vol. ${e.volume}${e.issue ? `(${e.issue})` : ""}` : "",
                e.pages ? `pp. ${e.pages}` : "",
              ].filter(Boolean).join(" · ")}
            </p>
          )}
          {e.doi && (
            <p className="text-[10px] text-gray-400 break-all">
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

function EvidenceSummaryStrip({ counts, hiddenCount }: { counts: EvidenceCounts; hiddenCount: number }) {
  const items: Array<{ key: EvidenceTier; count: number }> = (
    [
      { key: "direct",    count: counts.direct    ?? 0 },
      { key: "review",    count: counts.review    ?? 0 },
      { key: "guideline", count: counts.guideline ?? 0 },
      { key: "weak",      count: counts.weak      ?? 0 },
    ] as Array<{ key: EvidenceTier; count: number }>
  ).filter((i) => i.count > 0);

  if (items.length === 0 && hiddenCount === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-3.5 py-2 bg-slate-50 border-b border-gray-100">
      <span className="text-[10px] uppercase tracking-wide font-semibold text-slate-500 mr-1">
        Evidence mix:
      </span>
      {items.map((i) => {
        const s = TIER_STYLES[i.key];
        return (
          <span
            key={i.key}
            className={`text-[10.5px] font-medium px-2 py-0.5 rounded-full inline-flex items-center gap-1 ring-1 ${s.bg} ${s.text}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} aria-hidden />
            {i.count} {s.label.toLowerCase()}
          </span>
        );
      })}
      {hiddenCount > 0 && (
        <span className="text-[10.5px] text-slate-500 ml-1">
          · {hiddenCount} retrieved but not used
        </span>
      )}
    </div>
  );
}

function HiddenRefsDrawer({ hidden }: { hidden: CitationItem[] }) {
  const [open, setOpen] = useState(false);
  if (hidden.length === 0) return null;

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
      className="border-t border-gray-100 bg-slate-50/60"
    >
      <summary className="cursor-pointer px-4 py-2 text-[11px] font-medium text-slate-600 hover:text-slate-800 select-none">
        {open ? "▲ Hide" : "▼ Show"} {hidden.length} retrieved but not used
        <span className="ml-1.5 text-slate-400">
          (these were pulled during search but not directly relevant to the final answer)
        </span>
      </summary>
      <ol className="px-3 pb-3 pt-1 grid grid-cols-1 sm:grid-cols-2 gap-2 list-none m-0">
        {hidden.map((c) => (
          <li
            key={c.ref}
            className="text-[11px] text-slate-600 bg-white rounded-lg border border-gray-200 px-3 py-2"
          >
            <div className="font-medium text-slate-700 leading-snug">{c.title}</div>
            <div className="text-[10px] text-slate-500 italic mt-0.5">
              {c.journal}
              {c.year ? ` · ${c.year}` : ""}
              {c.study_type ? ` · ${c.study_type}` : ""}
            </div>
          </li>
        ))}
      </ol>
    </details>
  );
}

export default function ReferencesPanel({
  citations,
  liveResources,
  totalSources,
  hiddenReferences = [],
  evidenceCounts = {},
}: ReferencesPanelProps) {
  const [open, setOpen] = useState(true);

  if (citations.length === 0 && liveResources.length === 0) return null;

  const entries = buildEntries(citations, liveResources);
  const publishers = Array.from(new Set(entries.map((e) => e.publisher).filter(Boolean)));

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden bg-white">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 text-sm font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
        aria-expanded={open}
      >
        <span>
          📚 Evidence ({entries.length}
          {totalSources && totalSources > entries.length ? ` cited of ${totalSources} retrieved` : ""})
        </span>
        <span className="text-gray-400 text-xs">{open ? "▲ hide" : "▼ show"}</span>
      </button>

      {open && (
        <>
          <EvidenceSummaryStrip counts={evidenceCounts} hiddenCount={hiddenReferences.length} />

          <div className="px-3 py-3 bg-white">
            <ol className="grid grid-cols-1 sm:grid-cols-2 gap-2 list-none m-0 p-0">
              {entries.map((e) => (
                <RefCard key={e.ref} e={e} />
              ))}
            </ol>
          </div>

          <HiddenRefsDrawer hidden={hiddenReferences} />

          <div className="px-4 py-2 bg-slate-50 border-t border-gray-100 flex items-start gap-2">
            <span className="text-teal-600 text-sm shrink-0 mt-0.5">🔒</span>
            <p className="text-xs text-slate-500 leading-relaxed">
              <span className="font-semibold text-slate-700">Source integrity: </span>
              Grounded in peer-reviewed veterinary literature
              {publishers.length > 0 && <> ({publishers.join(", ")})</>}.
              Evidence tags reflect how directly each source supports the claim.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
