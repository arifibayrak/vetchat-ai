import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
      keyframes: {
        fadeIn:  { from: { opacity: "0" },                                          to: { opacity: "1" } },
        slideUp: { from: { opacity: "0", transform: "translateY(10px)" },           to: { opacity: "1", transform: "translateY(0)" } },
        scaleIn: { from: { opacity: "0", transform: "scale(0.95)" },                to: { opacity: "1", transform: "scale(1)" } },
        shimmer: { from: { backgroundPosition: "-200% 0" },                         to: { backgroundPosition: "200% 0" } },
      },
      animation: {
        "fade-in":  "fadeIn 0.25s ease-out both",
        "slide-up": "slideUp 0.3s ease-out both",
        "scale-in": "scaleIn 0.2s ease-out both",
        "shimmer":  "shimmer 1.5s infinite linear",
      },
    },
  },
  plugins: [],
};
export default config;
