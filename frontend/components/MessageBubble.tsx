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
}

const SECTION_COLORS: Record<string, string> = {
  "Overview":                 "border-slate-400 bg-slate-50 text-slate-800",
  "What the Research Shows":  "border-slate-400 bg-slate-50 text-slate-800",
  "Clinical Signs":           "border-slate-400 bg-slate-50 text-slate-800",
  "Management Approach":      "border-teal-400  bg-teal-50  text-teal-900",
  "Veterinary Recommendation":"border-teal-400  bg-teal-50  text-teal-900",
  "What Changed":             "border-amber-400 bg-amber-50 text-amber-900",
  "Updated Plan":             "border-teal-400  bg-teal-50  text-teal-900",
  "Unchanged":                "border-slate-300 bg-slate-50 text-slate-700",
  "Immediate Next Steps (next 30-60 min)": "border-rose-400 bg-rose-50 text-rose-900",
  "Immediate Next Steps":     "border-rose-400 bg-rose-50 text-rose-900",
  "Escalation Triggers":      "border-red-400  bg-red-50   text-red-900",
};

const SECTION_ICONS: Record<string, string> = {
  "Overview":                "🔬",
  "What the Research Shows": "📄",
  "Clinical Signs":          "🩺",
  "Management Approach":     "💊",
  "Veterinary Recommendation":"✅",
  "What Changed":            "🔄",
  "Updated Plan":            "📋",
  "Unchanged":               "✓",
  "Immediate Next Steps (next 30-60 min)": "⏱️",
  "Immediate Next Steps":    "⏱️",
  "Escalation Triggers":     "🚨",
};

function linkifyCitations(content: string): string {
  return content.replace(/\[(\d+)\]/g, (_match, n) => `[[${n}]](#citation-${n})`);
}

export default function MessageBubble({ message, isFollowUp = false }: MessageBubbleProps) {
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

            <ReferencesPanel
              citations={message.citations}
              liveResources={message.liveResources}
              totalSources={message.totalSources}
            />
            {message.flow && <AlgoFlow flow={message.flow} />}
          </>
      </div>
    </div>
  );
}
