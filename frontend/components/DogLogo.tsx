"use client";

interface DogLogoProps {
  size?: number;
  className?: string;
}

/**
 * Arlo — sitting dog logo, wider/bolder horizontal proportions.
 * viewBox 280×218: x-coordinates scaled 1.4× vs original for a chunkier,
 * more horizontal silhouette. Stroke weights increased for boldness.
 */
export default function DogLogo({ size = 40, className = "" }: DogLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 280 218"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Arlo"
      className={className}
    >
      {/* ── Tail (behind body, upper-left) ── */}
      <path
        d="M73 142 Q39 128 46 104 Q50 93 64 99 Q57 116 73 133"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="10"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* ── Body — wide and low ── */}
      <path
        d="M59 150 Q56 196 140 200 Q224 196 221 150 Q221 114 140 110 Q59 114 59 150Z"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="9"
        strokeLinejoin="round"
      />

      {/* ── Cream belly ── */}
      <path
        d="M106 170 Q140 184 174 170 L174 196 Q140 205 106 196 Z"
        fill="#F7F0D2"
        stroke="none"
      />

      {/* ── Left ear ── */}
      <path
        d="M104 38 Q70 18 53 50 Q38 78 73 92 Q98 88 109 62 Q112 46 104 38Z"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="9"
        strokeLinejoin="round"
      />
      {/* Left ear inner shadow */}
      <path
        d="M95 45 Q72 30 61 57 Q50 78 76 88 Q91 82 101 62 Q104 50 95 45Z"
        fill="#9A5520"
        stroke="none"
      />

      {/* ── Right ear ── */}
      <path
        d="M176 38 Q210 18 227 50 Q242 78 207 92 Q182 88 171 62 Q168 46 176 38Z"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="9"
        strokeLinejoin="round"
      />
      {/* Right ear inner shadow */}
      <path
        d="M185 45 Q208 30 219 57 Q230 78 204 88 Q189 82 179 62 Q176 50 185 45Z"
        fill="#9A5520"
        stroke="none"
      />

      {/* ── Head ── */}
      <circle
        cx="140"
        cy="76"
        r="60"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="9"
      />

      {/* ── Muzzle (dark brown) ── */}
      <ellipse cx="140" cy="97" rx="40" ry="29" fill="#8B4A18" />

      {/* ── Eyes ── */}
      <circle cx="110" cy="64" r="11" fill="#1a0800" />
      <circle cx="170" cy="64" r="11" fill="#1a0800" />
      {/* Eye highlights */}
      <circle cx="107" cy="61" r="4" fill="white" opacity="0.55" />
      <circle cx="167" cy="61" r="4" fill="white" opacity="0.55" />

      {/* ── Nose ── */}
      <ellipse cx="140" cy="84" rx="16" ry="13" fill="#1a0800" />
      {/* Nose gloss */}
      <ellipse cx="134" cy="80" rx="5" ry="3" fill="#555" opacity="0.35" />

      {/* ── Tongue ── */}
      <path
        d="M120 104 Q140 115 160 104 Q160 124 140 130 Q120 124 120 104Z"
        fill="#F472B6"
      />
      {/* Tongue crease */}
      <path
        d="M140 104 L140 129"
        stroke="#DB2777"
        strokeWidth="2.2"
        strokeLinecap="round"
      />

      {/* ── Collar (red band) ── */}
      <path
        d="M78 120 Q140 136 202 120 L200 133 Q140 149 80 133 Z"
        fill="#DC2626"
        stroke="#1a0800"
        strokeWidth="4"
        strokeLinejoin="round"
      />

      {/* ── Tag (gold disc) ── */}
      <circle
        cx="140"
        cy="152"
        r="12"
        fill="#EAB308"
        stroke="#1a0800"
        strokeWidth="3"
      />

      {/* ── Front paws ── */}
      <ellipse
        cx="94"
        cy="202"
        rx="30"
        ry="13"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="8"
      />
      <ellipse
        cx="186"
        cy="202"
        rx="30"
        ry="13"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="8"
      />
    </svg>
  );
}
