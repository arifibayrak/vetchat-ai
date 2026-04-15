import { ImageResponse } from "next/og";

export const size = { width: 64, height: 64 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <svg width="64" height="64" viewBox="0 0 280 218" xmlns="http://www.w3.org/2000/svg">
        {/* Tail */}
        <path d="M73 142 Q39 128 46 104 Q50 93 64 99 Q57 116 73 133" fill="#C07030" stroke="#1a0800" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" />
        {/* Body */}
        <path d="M59 150 Q56 196 140 200 Q224 196 221 150 Q221 114 140 110 Q59 114 59 150Z" fill="#C07030" stroke="#1a0800" stroke-width="9" />
        {/* Cream belly */}
        <path d="M106 170 Q140 184 174 170 L174 196 Q140 205 106 196 Z" fill="#F7F0D2" />
        {/* Left ear */}
        <path d="M104 38 Q70 18 53 50 Q38 78 73 92 Q98 88 109 62 Q112 46 104 38Z" fill="#C07030" stroke="#1a0800" stroke-width="9" />
        <path d="M95 45 Q72 30 61 57 Q50 78 76 88 Q91 82 101 62 Q104 50 95 45Z" fill="#9A5520" />
        {/* Right ear */}
        <path d="M176 38 Q210 18 227 50 Q242 78 207 92 Q182 88 171 62 Q168 46 176 38Z" fill="#C07030" stroke="#1a0800" stroke-width="9" />
        <path d="M185 45 Q208 30 219 57 Q230 78 204 88 Q189 82 179 62 Q176 50 185 45Z" fill="#9A5520" />
        {/* Head */}
        <circle cx="140" cy="76" r="60" fill="#C07030" stroke="#1a0800" stroke-width="9" />
        {/* Muzzle */}
        <ellipse cx="140" cy="97" rx="40" ry="29" fill="#8B4A18" />
        {/* Eyes */}
        <circle cx="110" cy="64" r="11" fill="#1a0800" />
        <circle cx="170" cy="64" r="11" fill="#1a0800" />
        <circle cx="107" cy="61" r="4" fill="white" fill-opacity="0.55" />
        <circle cx="167" cy="61" r="4" fill="white" fill-opacity="0.55" />
        {/* Nose */}
        <ellipse cx="140" cy="84" rx="16" ry="13" fill="#1a0800" />
        {/* Tongue */}
        <path d="M120 104 Q140 115 160 104 Q160 124 140 130 Q120 124 120 104Z" fill="#F472B6" />
        <path d="M140 104 L140 129" stroke="#DB2777" stroke-width="2.2" stroke-linecap="round" />
        {/* Collar */}
        <path d="M78 120 Q140 136 202 120 L200 133 Q140 149 80 133 Z" fill="#DC2626" stroke="#1a0800" stroke-width="4" />
        {/* Tag */}
        <circle cx="140" cy="152" r="12" fill="#EAB308" stroke="#1a0800" stroke-width="3" />
        {/* Paws */}
        <ellipse cx="94" cy="202" rx="30" ry="13" fill="#C07030" stroke="#1a0800" stroke-width="8" />
        <ellipse cx="186" cy="202" rx="30" ry="13" fill="#C07030" stroke="#1a0800" stroke-width="8" />
      </svg>
    ),
    { ...size }
  );
}
