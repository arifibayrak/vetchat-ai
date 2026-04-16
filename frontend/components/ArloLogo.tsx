interface ArloLogoProps {
  size?: number;
}

export default function ArloLogo({ size = 44 }: ArloLogoProps) {
  const textSize = Math.round(size * 0.82);
  return (
    <div className="flex items-center gap-1.5">
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path d="M12 1 L23 23 L1 23 Z" fill="#2dd4bf" />
        <path d="M12 6 L19 23 L5 23 Z" fill="#ffffff" />
        <rect x="5" y="15" width="14" height="3" fill="#2dd4bf" />
      </svg>
      <span
        className="font-black text-teal-400 leading-none"
        style={{ fontSize: textSize, letterSpacing: "-0.03em" }}
      >
        Arlo
      </span>
    </div>
  );
}
