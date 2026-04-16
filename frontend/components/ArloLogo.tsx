interface ArloLogoProps {
  height?: number;
  className?: string;
}

export default function ArloLogo({ height = 40, className = "" }: ArloLogoProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/arlo-logo.png"
      alt="Arlo"
      height={height}
      style={{ height, width: "auto" }}
      className={className}
    />
  );
}
