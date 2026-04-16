import { ImageResponse } from "next/og";

export const size = { width: 64, height: 64 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 64,
          height: 64,
          background: "#0f172a",
          borderRadius: 14,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="40" height="40" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M12 1 L23 23 L1 23 Z"
            fill="#2dd4bf"
          />
          <path
            d="M12 6 L19 23 L5 23 Z"
            fill="#0f172a"
          />
          <rect x="5" y="15" width="14" height="3" fill="#2dd4bf" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
