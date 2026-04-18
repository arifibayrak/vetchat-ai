"use client";

interface Props {
  quality: "strong" | "moderate" | "weak";
  citedCount: number;
  totalSources: number;
}

const CONFIG = {
  strong:   { dot: "bg-emerald-500", label: "Strong",   style: "bg-emerald-50 border-emerald-200 text-emerald-800" },
  moderate: { dot: "bg-amber-400",   label: "Moderate", style: "bg-amber-50 border-amber-200 text-amber-800" },
  weak:     { dot: "bg-red-400",     label: "Limited",  style: "bg-red-50 border-red-200 text-red-800" },
} as const;

export default function EvidenceQualityBadge({ quality, citedCount, totalSources }: Props) {
  const { dot, label, style } = CONFIG[quality];
  const showRatio = totalSources > 0;

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${style}`}>
      <span className={`w-2 h-2 rounded-full shrink-0 ${dot}`} aria-hidden />
      <span>Evidence: {label}</span>
      {showRatio && (
        <span className="opacity-60 font-normal">
          · {citedCount} of {totalSources} sources cited
        </span>
      )}
    </div>
  );
}
