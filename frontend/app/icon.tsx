import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 8,
          background: "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Minimal dog face at 32px */}
        <svg width="24" height="24" viewBox="0 0 64 64" fill="none">
          {/* Left ear */}
          <ellipse cx="14" cy="24" rx="9" ry="14" fill="#ccfbf1" transform="rotate(-15 14 24)" />
          {/* Right ear */}
          <ellipse cx="50" cy="24" rx="9" ry="14" fill="#ccfbf1" transform="rotate(15 50 24)" />
          {/* Head */}
          <circle cx="32" cy="36" r="22" fill="white" />
          {/* Left eye */}
          <circle cx="23" cy="32" r="3.5" fill="#134e4a" />
          {/* Right eye */}
          <circle cx="41" cy="32" r="3.5" fill="#134e4a" />
          {/* Nose */}
          <ellipse cx="32" cy="41" rx="5" ry="3.5" fill="#134e4a" />
          {/* Smile */}
          <path d="M25 47 Q32 53 39 47" stroke="#134e4a" strokeWidth="2.5" strokeLinecap="round" fill="none" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
