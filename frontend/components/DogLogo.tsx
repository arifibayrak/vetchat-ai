"use client";

interface DogLogoProps {
  size?: number;
  className?: string;
}

/**
 * Arlo — sitting dog logo, pure flat design, teal palette.
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
      {/* ── Tail ── */}
      <path
        d="M73 142 Q39 128 46 104 Q50 93 64 99 Q57 116 73 133"
        fill="#0d9488"
      />

      {/* ── Body ── */}
      <path
        d="M59 150 Q56 196 140 200 Q224 196 221 150 Q221 114 140 110 Q59 114 59 150Z"
        fill="#0d9488"
      />

      {/* ── Belly ── */}
      <path
        d="M106 170 Q140 184 174 170 L174 196 Q140 205 106 196 Z"
        fill="#ccfbf1"
      />

      {/* ── Left ear ── */}
      <path
        d="M104 38 Q70 18 53 50 Q38 78 73 92 Q98 88 109 62 Q112 46 104 38Z"
        fill="#0d9488"
      />
      <path
        d="M95 45 Q72 30 61 57 Q50 78 76 88 Q91 82 101 62 Q104 50 95 45Z"
        fill="#0f766e"
      />

      {/* ── Right ear ── */}
      <path
        d="M176 38 Q210 18 227 50 Q242 78 207 92 Q182 88 171 62 Q168 46 176 38Z"
        fill="#0d9488"
      />
      <path
        d="M185 45 Q208 30 219 57 Q230 78 204 88 Q189 82 179 62 Q176 50 185 45Z"
        fill="#0f766e"
      />

      {/* ── Head ── */}
      <circle cx="140" cy="76" r="60" fill="#0d9488" />

      {/* ── Muzzle ── */}
      <ellipse cx="140" cy="97" rx="40" ry="29" fill="#0f766e" />

      {/* ── Eyes ── */}
      <circle cx="110" cy="64" r="11" fill="#134e4a" />
      <circle cx="170" cy="64" r="11" fill="#134e4a" />
      <circle cx="107" cy="61" r="4" fill="white" opacity="0.55" />
      <circle cx="167" cy="61" r="4" fill="white" opacity="0.55" />

      {/* ── Nose ── */}
      <ellipse cx="140" cy="84" rx="16" ry="13" fill="#134e4a" />
      <ellipse cx="134" cy="80" rx="5" ry="3" fill="#5eead4" opacity="0.3" />

      {/* ── Tongue ── */}
      <path
        d="M120 104 Q140 115 160 104 Q160 124 140 130 Q120 124 120 104Z"
        fill="#f472b6"
      />
      <path
        d="M140 104 L140 129"
        stroke="#db2777"
        strokeWidth="2.2"
        strokeLinecap="round"
      />

      {/* ── Collar ── */}
      <path
        d="M78 120 Q140 136 202 120 L200 133 Q140 149 80 133 Z"
        fill="#5eead4"
      />

      {/* ── Tag ── */}
      <circle cx="140" cy="152" r="12" fill="#ccfbf1" />

      {/* ── Front paws ── */}
      <ellipse cx="94" cy="202" rx="30" ry="13" fill="#0d9488" />
      <ellipse cx="186" cy="202" rx="30" ry="13" fill="#0d9488" />
    </svg>
  );
}
