"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/types/chat";
import AlgoFlow from "./AlgoFlow";
import EmergencyBanner from "./EmergencyBanner";
import EmergencyPreliminaryCard from "./EmergencyPreliminaryCard";
import EvidenceQualityBadge from "./EvidenceQualityBadge";
import ReferencesPanel from "./ReferencesPanel";
import LoadingSteps from "./LoadingSteps";

interface MessageBubbleProps {
  message: Message;
  isFollowUp?: boolean;
  onRetry?: (originalQuery?: string) => void;
  onExpandSearch?: (originalQuery?: string) => void;
}

const SECTION_COLORS: Record<string, string> = {
  // Legacy 5-section format (still supported for any legacy answers)
  "Overview":                 "border-slate-400 bg-slate-50 text-slate-800",
  "What the Research Shows":  "border-slate-400 bg-slate-50 text-slate-800",
  "Clinical Signs":           "border-slate-400 bg-slate-50 text-slate-800",
  "Management Approach":      "border-teal-400  bg-teal-50  text-teal-900",
  "Veterinary Recommendation":"border-teal-400  bg-teal-50  text-teal-900",
  "Clinical Recommendations": "border-teal-400  bg-teal-50  text-teal-900",
  // Initial-query schema
  "Immediate Priorities":      "border-rose-400  bg-rose-50  text-rose-900",
  "Clinical Frame":            "border-slate-400 bg-slate-50 text-slate-800",
  "Direct Evidence":           "border-emerald-400 bg-emerald-50 text-emerald-900",
  "Evidence-Based Findings":   "border-emerald-400 bg-emerald-50 text-emerald-900",
  "Standard-of-Care Guidance": "border-blue-400  bg-blue-50  text-blue-900",
  "Monitoring & Escalation":   "border-amber-400 bg-amber-50 text-amber-900",
  "Evidence Gaps":             "border-orange-400 bg-orange-50 text-orange-900",
  "References":                "border-violet-400 bg-violet-50 text-violet-900",
  // Emergency-mode sections
  "Immediate Stabilisation":   "border-rose-400  bg-rose-50  text-rose-900",
  "Immediate Stabilization":   "border-rose-400  bg-rose-50  text-rose-900",
  "Targeted Diagnostics":      "border-slate-400 bg-slate-50 text-slate-800",
  "First-line Management":     "border-teal-400  bg-teal-50  text-teal-900",
  "Escalation Triggers":       "border-red-400   bg-red-50   text-red-900",
  // Follow-up sections
  "What Changed":                      "border-amber-400 bg-amber-50 text-amber-900",
  "What Changes in Management Now":    "border-teal-400  bg-teal-50  text-teal-900",
  "Management Changes Now":            "border-teal-400  bg-teal-50  text-teal-900",
  "Updated Plan":                      "border-teal-400  bg-teal-50  text-teal-900",
  "Unchanged":                         "border-slate-300 bg-slate-50 text-slate-700",
  "What Stays the Same":               "border-slate-300 bg-slate-50 text-slate-700",
  "Monitoring for the Next Interval":  "border-amber-400 bg-amber-50 text-amber-900",
  "Monitoring Plan":                   "border-amber-400 bg-amber-50 text-amber-900",
  "Escalation / Referral Triggers":    "border-red-400   bg-red-50   text-red-900",
  "Discharge / Escalation Triggers":   "border-red-400   bg-red-50   text-red-900",
  "Evidence Quality Note":             "border-slate-300 bg-slate-50 text-slate-600",
  "Immediate Next Steps (next 30-60 min)": "border-rose-400 bg-rose-50 text-rose-900",
  "Immediate Next Steps":              "border-rose-400 bg-rose-50 text-rose-900",
  // Fallback-mode sections
  "Safe Clinical Summary":             "border-amber-400 bg-amber-50 text-amber-900",
  "What to Do Next":                   "border-teal-400  bg-teal-50  text-teal-900",
};

const SECTION_ICONS: Record<string, string> = {
  "Overview":                "🔬",
  "What the Research Shows": "📄",
  "Clinical Signs":          "🩺",
  "Management Approach":     "💊",
  "Veterinary Recommendation":"✅",
  "Clinical Recommendations":"✅",
  "Immediate Priorities":     "⚡",
  "Clinical Frame":           "🔬",
  "Direct Evidence":          "📄",
  "Evidence-Based Findings":  "📄",
  "Standard-of-Care Guidance":"💡",
  "Monitoring & Escalation":  "🩺",
  "Evidence Gaps":            "⚠️",
  "References":               "📚",
  "Immediate Stabilisation":  "🚑",
  "Immediate Stabilization":  "🚑",
  "Targeted Diagnostics":     "🔎",
  "First-line Management":    "💊",
  "Escalation Triggers":      "🚨",
  "What Changed":                      "🔄",
  "What Changes in Management Now":    "📋",
  "Management Changes Now":            "📋",
  "Updated Plan":                      "📋",
  "Unchanged":                         "✓",
  "What Stays the Same":               "✓",
  "Monitoring for the Next Interval":  "📊",
  "Monitoring Plan":                   "📊",
  "Escalation / Referral Triggers":    "🚨",
  "Discharge / Escalation Triggers":   "🚨",
  "Evidence Quality Note":             "📚",
  "Immediate Next Steps (next 30-60 min)": "⏱️",
  "Immediate Next Steps":              "⏱️",
  "Safe Clinical Summary":             "🛟",
  "What to Do Next":                   "➡️",
};

// Inline evidence tags produced by the system prompt. Rendered as compact
// coloured pills so they read as badges, not bracketed clutter in the prose.
const EVIDENCE_TAG_STYLES: Record<string, string> = {
  "Direct evidence":      "bg-emerald-100 text-emerald-800 ring-emerald-200",
  "Review":               "bg-sky-100     text-sky-800     ring-sky-200",
  "Guideline/Consensus":  "bg-violet-100  text-violet-800  ring-violet-200",
  "Consensus":            "bg-violet-100  text-violet-800  ring-violet-200",
  "Weak indirect":        "bg-amber-100   text-amber-800   ring-amber-200",
  "No direct evidence":   "bg-slate-100   text-slate-600   ring-slate-200",
  "Gap":                  "bg-orange-100  text-orange-800  ring-orange-200",
};

const EVIDENCE_TAG_PATTERN =
  /\[(Direct evidence|Review|Guideline\/Consensus|Consensus|Weak indirect|No direct evidence|Gap)\]/g;

function linkifyCitations(content: string): string {
  // Numeric citations → anchor links to the reference panel
  let out = content.replace(/\[(\d+)\]/g, (_m, n) => `[[${n}]](#citation-${n})`);
  // Evidence tags → custom `<evtag>` pseudo-element; react-markdown rewrites
  // it via the custom code component below. Using backticks keeps it in
  // text phase so GFM tables + lists still parse normally.
  out = out.replace(EVIDENCE_TAG_PATTERN, (_m, tag) => `\`evtag::${tag}\``);
  return out;
}

function EvidenceTagPill({ tag }: { tag: string }) {
  const style = EVIDENCE_TAG_STYLES[tag] ?? "bg-slate-100 text-slate-600 ring-slate-200";
  return (
    <span
      className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium ring-1 align-baseline mx-0.5 ${style}`}
    >
      {tag}
    </span>
  );
}

function FailureBubble({
  message,
  onRetry,
  onExpandSearch,
}: {
  message: Message;
  onRetry?: (q?: string) => void;
  onExpandSearch?: (q?: string) => void;
}) {
  const isTimeout = message.failureKind === "timeout";
  const title = isTimeout
    ? "Generation took too long"
    : message.failureKind === "server"
      ? "Service is starting up"
      : "Something went wrong";
  const body = message.failureMessage
    || "We couldn't complete your answer. Here are safe next steps while you decide how to continue.";

  return (
    <div className="flex justify-start w-full animate-fade-in">
      <div className="w-full max-w-2xl rounded-2xl bg-white border border-amber-200 px-5 py-4 shadow-sm">
        <div className="flex items-start gap-2">
          <span className="text-xl leading-none" aria-hidden>🛟</span>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-amber-900">{title}</h3>
            <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">{body}</p>

            <div className="mt-3 rounded-lg bg-amber-50 border border-amber-100 px-3 py-2 text-xs text-amber-900 leading-relaxed">
              <p className="font-medium mb-0.5">Safe fallback guidance</p>
              <p>
                If this is an active case, fall back to your clinic's standard stabilisation
                protocol and reassess in 10-15 minutes. Arlo's literature synthesis is
                incomplete for this turn — don't act on inferred specifics until you've
                re-queried with a cleaner context.
              </p>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {onRetry && (
                <button
                  onClick={() => onRetry(message.originalQuery)}
                  className="px-3 py-1.5 rounded-lg bg-teal-600 text-white text-xs font-medium hover:bg-teal-700 transition-colors"
                >
                  ↻ Retry same query
                </button>
              )}
              {onExpandSearch && (
                <button
                  onClick={() => onExpandSearch(message.originalQuery)}
                  className="px-3 py-1.5 rounded-lg bg-white border border-teal-300 text-teal-700 text-xs font-medium hover:bg-teal-50 transition-colors"
                >
                  🔍 Expand search
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FallbackBanner({ kind }: { kind: NonNullable<Message["fallbackKind"]> }) {
  const copy: Record<NonNullable<Message["fallbackKind"]>, { title: string; body: string; tint: string }> = {
    no_retrieval: {
      title: "Literature synthesis incomplete",
      body: "No peer-reviewed sources were retrieved for this query. Answer below is consensus-based.",
      tint: "bg-amber-50 border-amber-200 text-amber-900",
    },
    guard_blocked: {
      title: "Answer rewritten for safety",
      body: "The initial synthesis didn't ground in retrieved literature. Showing a consensus-based version instead.",
      tint: "bg-amber-50 border-amber-200 text-amber-900",
    },
    timeout_partial: {
      title: "Partial answer — generation interrupted",
      body: "Synthesis ran long. The content below is what was produced before the timeout.",
      tint: "bg-orange-50 border-orange-200 text-orange-900",
    },
  };
  const c = copy[kind];
  return (
    <div className={`rounded-lg border px-3 py-2 mb-3 ${c.tint}`}>
      <p className="text-xs font-semibold">⚠️ {c.title}</p>
      <p className="text-[11px] mt-0.5 leading-relaxed">{c.body}</p>
    </div>
  );
}

export default function MessageBubble({
  message,
  isFollowUp = false,
  onRetry,
  onExpandSearch,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end animate-slide-up">
        <div className="max-w-xl rounded-2xl bg-teal-600 px-4 py-2 text-white text-sm shadow">
          {message.content}
        </div>
      </div>
    );
  }

  // ── Failure recovery bubble ────────────────────────────────────────────────
  // Replaces the old "silently remove bubble + red banner" path. The user
  // always gets a usable surface with Retry / Expand-search actions.
  if (message.failureKind) {
    return <FailureBubble message={message} onRetry={onRetry} onExpandSearch={onExpandSearch} />;
  }

  if (message.isLoading) {
    return (
      <div className="flex justify-start w-full animate-fade-in">
        <div className="w-full max-w-md rounded-2xl bg-white border border-gray-200 px-5 py-4 shadow-sm">
          {message.emergencyPreliminary && (
            <EmergencyPreliminaryCard card={message.emergencyPreliminary} />
          )}
          {message.isSlowQuery && (
            <div className="mb-3 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800">
              ⏳ Still searching… this query is taking longer than usual. Please wait.
            </div>
          )}
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Searching literature and preparing your answer…
          </p>
          <LoadingSteps steps={message.steps ?? []} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start w-full animate-slide-up">
      <div className="w-full max-w-3xl rounded-2xl bg-white border border-gray-200 px-5 py-4 shadow-sm text-sm space-y-1">
        {isFollowUp && (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200 px-2.5 py-1 text-[11px] font-semibold text-amber-800 mb-2">
            <span aria-hidden>🔄</span>
            <span>Case update</span>
          </div>
        )}

        {message.emergencyPreliminary && (
          <EmergencyPreliminaryCard card={message.emergencyPreliminary} />
        )}

        {message.emergency && (
          <EmergencyBanner />
        )}

        {message.fallbackKind && <FallbackBanner kind={message.fallbackKind} />}

        {message.retrievalQuality && (
          <div className="mb-3">
            <EvidenceQualityBadge
              quality={message.retrievalQuality}
              citedCount={message.citedCount ?? 0}
              totalSources={message.totalSources ?? 0}
            />
          </div>
        )}

        <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h2({ children }) {
                  const label = String(children);
                  const colorClass = SECTION_COLORS[label] ?? "border-slate-300 bg-slate-50 text-slate-800";
                  const icon = SECTION_ICONS[label] ?? "•";
                  return (
                    <div className={`rounded-lg border-l-4 px-4 py-2 mt-4 mb-2 font-semibold text-sm ${colorClass}`}>
                      {icon} {label}
                    </div>
                  );
                },
                p({ children }) {
                  return <p className="text-gray-700 leading-relaxed text-sm mb-2">{children}</p>;
                },
                ul({ children }) {
                  return <ul className="space-y-1 mb-2">{children}</ul>;
                },
                li({ children }) {
                  return (
                    <li className="flex gap-2 text-gray-700 text-sm leading-relaxed">
                      <span className="text-teal-500 mt-0.5 shrink-0">▸</span>
                      <span>{children}</span>
                    </li>
                  );
                },
                strong({ children }) {
                  return <strong className="font-semibold text-gray-900">{children}</strong>;
                },
                code({ children, className }) {
                  const text = String(children ?? "");
                  // Evidence-tag pseudo-element produced by linkifyCitations
                  if (text.startsWith("evtag::")) {
                    return <EvidenceTagPill tag={text.slice(7)} />;
                  }
                  return (
                    <code className={`bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-[12px] font-mono ${className ?? ""}`}>
                      {children}
                    </code>
                  );
                },
                a({ href, children }) {
                  const isAnchor = href?.startsWith("#");
                  return (
                    <a
                      href={href}
                      target={isAnchor ? undefined : "_blank"}
                      rel={isAnchor ? undefined : "noopener noreferrer"}
                      className={isAnchor
                        ? "inline-flex items-center justify-center w-5 h-5 rounded-full bg-violet-600 text-white text-xs font-bold hover:bg-violet-800 transition-colors cursor-pointer align-baseline mx-0.5"
                        : "text-teal-600 underline hover:text-teal-800"
                      }
                    >
                      {children}
                    </a>
                  );
                },
                table({ children }) {
                  return (
                    <div className="overflow-x-auto my-3">
                      <table className="w-full text-xs border-collapse">{children}</table>
                    </div>
                  );
                },
                thead({ children }) {
                  return <thead className="bg-teal-50">{children}</thead>;
                },
                th({ children }) {
                  return (
                    <th className="border border-gray-200 px-3 py-1.5 text-left font-semibold text-teal-800 whitespace-nowrap">
                      {children}
                    </th>
                  );
                },
                td({ children }) {
                  return (
                    <td className="border border-gray-200 px-3 py-1.5 text-gray-700 leading-snug">
                      {children}
                    </td>
                  );
                },
                tr({ children }) {
                  return <tr className="even:bg-gray-50">{children}</tr>;
                },
                hr() {
                  return <hr className="border-gray-200 my-3" />;
                },
              }}
            >
              {linkifyCitations(message.content)}
            </ReactMarkdown>

            {message.isStreaming && (
              <span className="inline-block w-1.5 h-4 bg-teal-600 align-middle ml-0.5 animate-pulse" aria-hidden />
            )}

            <ReferencesPanel
              citations={message.citations}
              liveResources={message.liveResources}
              totalSources={message.totalSources}
              hiddenReferences={message.hiddenReferences}
              evidenceCounts={message.evidenceCounts}
            />
            {message.flow && <AlgoFlow flow={message.flow} />}
          </>
      </div>
    </div>
  );
}
