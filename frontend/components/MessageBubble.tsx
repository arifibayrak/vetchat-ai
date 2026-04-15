"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/types/chat";
import AlgoFlow from "./AlgoFlow";
import EmergencyBanner from "./EmergencyBanner";
import ReferencesPanel from "./ReferencesPanel";
import LoadingSteps from "./LoadingSteps";

interface MessageBubbleProps {
  message: Message;
}

const SECTION_COLORS: Record<string, string> = {
  "Overview":                 "border-slate-400 bg-slate-50 text-slate-800",
  "What the Research Shows":  "border-slate-400 bg-slate-50 text-slate-800",
  "Clinical Signs":           "border-slate-400 bg-slate-50 text-slate-800",
  "Management Approach":      "border-teal-400  bg-teal-50  text-teal-900",
  "Veterinary Recommendation":"border-teal-400  bg-teal-50  text-teal-900",
};

const SECTION_ICONS: Record<string, string> = {
  "Overview":                "🔬",
  "What the Research Shows": "📄",
  "Clinical Signs":          "🩺",
  "Management Approach":     "💊",
  "Veterinary Recommendation":"✅",
};

function linkifyCitations(content: string): string {
  return content.replace(/\[(\d+)\]/g, (_match, n) => `[[${n}]](#citation-${n})`);
}

export default function MessageBubble({ message }: MessageBubbleProps) {
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
        {message.emergency && message.resources.length > 0 && (
          <EmergencyBanner resources={message.resources} />
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
                hr() {
                  return <hr className="border-gray-200 my-3" />;
                },
              }}
            >
              {linkifyCitations(message.content)}
            </ReactMarkdown>

            <ReferencesPanel citations={message.citations} liveResources={message.liveResources} />
            {message.flow && <AlgoFlow flow={message.flow} />}
          </>
      </div>
    </div>
  );
}
