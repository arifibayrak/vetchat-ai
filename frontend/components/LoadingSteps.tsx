"use client";

import type { ProgressStep } from "@/types/chat";

interface LoadingStepsProps {
  steps: ProgressStep[];
}

export default function LoadingSteps({ steps }: LoadingStepsProps) {
  return (
    <div className="space-y-2 py-1">
      {steps.map((s, i) => {
        const isActive = i === steps.length - 1;
        const isDone = !isActive;

        return (
          <div key={i} className="flex items-center gap-3 animate-slide-up">
            {/* Icon / spinner */}
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 transition-all duration-300
                ${isDone ? "bg-green-100 text-green-600" : "bg-blue-100 text-blue-600"}`}
            >
              {isDone ? (
                <span className="transition-all duration-300">✓</span>
              ) : (
                <span className="animate-spin inline-block">⟳</span>
              )}
            </div>

            {/* Label */}
            <div className="flex-1">
              <p
                className={`text-sm font-medium transition-all duration-300
                  ${isDone ? "text-gray-400 line-through" : "text-gray-800"}`}
              >
                {s.icon} {s.label}
              </p>

              {/* Active progress bar */}
              {isActive && (
                <div className="mt-1 h-1 w-full bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-400 rounded-full animate-pulse w-2/3 transition-all duration-500" />
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* Waiting dots if no steps yet */}
      {steps.length === 0 && (
        <div className="flex items-center gap-2 text-gray-400 text-sm animate-fade-in">
          <span className="inline-flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce inline-block" />
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce animation-delay-150 inline-block" />
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce animation-delay-300 inline-block" />
          </span>
          <span>Connecting…</span>
        </div>
      )}
    </div>
  );
}
