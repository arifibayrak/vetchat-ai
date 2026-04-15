"use client";

interface DogLogoProps {
  size?: number;
  className?: string;
}

/**
 * Lenny — sitting dog logo, no background, thick-outline cartoon style.
 * Matches the reference: warm brown fur, dark muzzle, red collar, gold tag, pink tongue.
 */
export default function DogLogo({ size = 40, className = "" }: DogLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 218"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Lenny"
      className={className}
    >
      {/* ── Tail (behind body, upper-left) ── */}
      <path
        d="M52 142 Q28 128 33 104 Q36 93 46 99 Q41 116 52 133"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* ── Body ── */}
      <path
        d="M42 150 Q40 196 100 200 Q160 196 158 150 Q158 114 100 110 Q42 114 42 150Z"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="7"
        strokeLinejoin="round"
      />

      {/* ── Cream belly between front legs ── */}
      <path
        d="M76 170 Q100 182 124 170 L124 196 Q100 203 76 196 Z"
        fill="#F7F0D2"
        stroke="none"
      />

      {/* ── Left ear (viewer left, behind head) ── */}
      <path
        d="M74 38 Q50 20 38 50 Q27 76 52 90 Q70 86 78 62 Q80 46 74 38Z"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="7"
        strokeLinejoin="round"
      />
      {/* Left ear inner shadow */}
      <path
        d="M68 44 Q52 32 44 56 Q36 76 55 86 Q66 80 72 62 Q74 50 68 44Z"
        fill="#9A5520"
        stroke="none"
      />

      {/* ── Right ear (viewer right) ── */}
      <path
        d="M126 38 Q150 20 162 50 Q173 76 148 90 Q130 86 122 62 Q120 46 126 38Z"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="7"
        strokeLinejoin="round"
      />
      {/* Right ear inner shadow */}
      <path
        d="M132 44 Q148 32 156 56 Q164 76 145 86 Q134 80 128 62 Q126 50 132 44Z"
        fill="#9A5520"
        stroke="none"
      />

      {/* ── Head ── */}
      <circle
        cx="100"
        cy="76"
        r="54"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="7"
      />

      {/* ── Muzzle (dark brown) ── */}
      <ellipse cx="100" cy="96" rx="30" ry="26" fill="#8B4A18" />

      {/* ── Eyes ── */}
      <circle cx="78" cy="65" r="9" fill="#1a0800" />
      <circle cx="122" cy="65" r="9" fill="#1a0800" />
      {/* Eye highlights */}
      <circle cx="75" cy="62" r="3" fill="white" opacity="0.55" />
      <circle cx="119" cy="62" r="3" fill="white" opacity="0.55" />

      {/* ── Nose ── */}
      <ellipse cx="100" cy="84" rx="14" ry="12" fill="#1a0800" />
      {/* Nose gloss */}
      <ellipse cx="95" cy="80" rx="4.5" ry="2.5" fill="#555" opacity="0.35" />

      {/* ── Tongue ── */}
      <path
        d="M86 102 Q100 110 114 102 Q114 120 100 125 Q86 120 86 102Z"
        fill="#F472B6"
      />
      {/* Tongue crease */}
      <path
        d="M100 102 L100 124"
        stroke="#DB2777"
        strokeWidth="1.8"
        strokeLinecap="round"
      />

      {/* ── Collar (red band) ── */}
      <path
        d="M56 120 Q100 134 144 120 L142 133 Q100 147 58 133 Z"
        fill="#DC2626"
        stroke="#1a0800"
        strokeWidth="3.5"
        strokeLinejoin="round"
      />

      {/* ── Tag (gold disc) ── */}
      <circle
        cx="100"
        cy="148"
        r="10"
        fill="#EAB308"
        stroke="#1a0800"
        strokeWidth="2.5"
      />

      {/* ── Front paws ── */}
      <ellipse
        cx="67"
        cy="200"
        rx="24"
        ry="13"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="6"
      />
      <ellipse
        cx="133"
        cy="200"
        rx="24"
        ry="13"
        fill="#C07030"
        stroke="#1a0800"
        strokeWidth="6"
      />
    </svg>
  );
}
