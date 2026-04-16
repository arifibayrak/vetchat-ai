interface ArloLogoProps {
  height?: number;
  className?: string;
}

export default function ArloLogo({ height = 40, className = "" }: ArloLogoProps) {
  return (
    <svg
      viewBox="0 0 360 110"
      height={height}
      style={{ height, width: "auto" }}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Arlo"
    >
      {/* Geometric A — outer triangle minus inner V notch */}
      <path
        d="M68 4 L136 106 L110 106 L68 34 L26 106 L0 106 Z"
        fill="#21CBB2"
      />
      {/* rlo — bold rounded text */}
      <text
        x="148"
        y="103"
        fontFamily="'Arial Black', 'Helvetica Neue', Arial, sans-serif"
        fontWeight="900"
        fontSize="95"
        fill="#21CBB2"
      >
        rlo
      </text>
    </svg>
  );
}
