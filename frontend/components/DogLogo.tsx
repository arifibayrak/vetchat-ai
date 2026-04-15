"use client";

interface DogLogoProps {
  size?: number;
  className?: string;
}

/**
 * Lenny's dog logo — minimal line-art dog face, teal palette.
 * Use `size` to scale; defaults to 32px.
 */
export default function DogLogo({ size = 32, className = "" }: DogLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Lenny dog logo"
    >
      {/* Left floppy ear */}
      <ellipse
        cx="14"
        cy="24"
        rx="9"
        ry="14"
        fill="#0d9488"
        transform="rotate(-15 14 24)"
      />
      {/* Right floppy ear */}
      <ellipse
        cx="50"
        cy="24"
        rx="9"
        ry="14"
        fill="#0d9488"
        transform="rotate(15 50 24)"
      />
      {/* Head */}
      <circle cx="32" cy="36" r="22" fill="#ffffff" />
      <circle cx="32" cy="36" r="22" fill="#f0fdfa" stroke="#0d9488" strokeWidth="2" />
      {/* Left eye */}
      <circle cx="23" cy="32" r="3" fill="#134e4a" />
      <circle cx="24" cy="31" r="1" fill="#ffffff" />
      {/* Right eye */}
      <circle cx="41" cy="32" r="3" fill="#134e4a" />
      <circle cx="42" cy="31" r="1" fill="#ffffff" />
      {/* Nose */}
      <ellipse cx="32" cy="41" rx="5" ry="3.5" fill="#134e4a" />
      {/* Smile */}
      <path
        d="M25 47 Q32 53 39 47"
        stroke="#134e4a"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
      {/* Left cheek blush */}
      <ellipse cx="18" cy="43" rx="5" ry="3" fill="#f0abfc" opacity="0.35" />
      {/* Right cheek blush */}
      <ellipse cx="46" cy="43" rx="5" ry="3" fill="#f0abfc" opacity="0.35" />
    </svg>
  );
}
