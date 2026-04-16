"use client";

import type { FlowData, FlowStep } from "@/types/chat";

function Arrow() {
  return (
    <div className="flex flex-col items-center my-0.5">
      <div className="w-px h-3 bg-teal-400/60" />
      <svg width="10" height="6" viewBox="0 0 10 6">
        <polygon points="0,0 10,0 5,6" fill="#2dd4bf" opacity="0.8" />
      </svg>
    </div>
  );
}

function FlowNode({ step, isLast }: { step: FlowStep; isLast: boolean }) {
  if (step.type === "node") {
    return (
      <div className="flex flex-col items-center">
        <div
          className={`w-full rounded-xl px-3 py-2 text-center border ${
            step.highlight
              ? "bg-teal-50 border-teal-400 text-teal-800"
              : "bg-gray-50 border-gray-200 text-gray-700"
          }`}
        >
          <p className={`text-xs leading-snug ${step.highlight ? "font-semibold" : ""}`}>
            {step.text}
          </p>
          {step.sub && (
            <p className="text-[10px] text-gray-400 mt-0.5 leading-snug">{step.sub}</p>
          )}
        </div>
        {!isLast && <Arrow />}
      </div>
    );
  }

  if (step.type === "branch") {
    return (
      <div className="flex flex-col items-center">
        <div className="flex gap-1.5 w-full">
          {step.items.map((item) => (
            <div
              key={item}
              className="flex-1 rounded-lg px-2 py-1.5 text-center bg-blue-50 border border-blue-100 text-blue-600 text-[10px] font-medium"
            >
              {item}
            </div>
          ))}
        </div>
        {!isLast && <Arrow />}
      </div>
    );
  }

  if (step.type === "note") {
    return (
      <div className="flex flex-col items-center">
        <div className="flex items-center gap-2 w-full py-0.5">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-[10px] text-teal-600 italic flex-shrink-0">{step.text}</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>
        {!isLast && <Arrow />}
      </div>
    );
  }

  return null;
}

export default function AlgoFlow({ flow }: { flow: FlowData }) {
  return (
    <div className="mt-4 rounded-2xl border border-gray-200 bg-white overflow-hidden shadow-sm animate-fade-in">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 bg-gray-50 flex items-center gap-2">
        <span className="text-base">{flow.icon}</span>
        <div>
          <p className="text-xs font-semibold text-gray-800">{flow.title}</p>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide">Clinical Algorithm</p>
        </div>
      </div>

      {/* Flow steps */}
      <div className="px-4 py-4 flex flex-col">
        {flow.steps.map((step, i) => (
          <FlowNode key={i} step={step} isLast={i === flow.steps.length - 1} />
        ))}
      </div>

      {/* Source footer */}
      {flow.source && (
        <div className="px-4 py-2.5 border-t border-gray-100 flex items-center gap-1.5">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          <p className="text-[10px] text-gray-400">{flow.source}</p>
        </div>
      )}
    </div>
  );
}
