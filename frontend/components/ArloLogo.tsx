import Image from "next/image";

interface ArloLogoProps {
  height?: number;
  className?: string;
}

export default function ArloLogo({ height = 40, className = "" }: ArloLogoProps) {
  return (
    <Image
      src="/arlo-logo.png"
      alt="Arlo"
      height={height}
      width={height * 3.2}
      className={className}
      priority
    />
  );
}
