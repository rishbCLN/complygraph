import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0e14",
        panel: "#111826",
        "panel-2": "#0f1520",
        border: "#1f2937",
        muted: "#8b95a7",
        fg: "#e5e9f0",
        accent: "#3b82f6",
        "accent-2": "#2563eb",
        critical: "#ef4444",
        high: "#f97316",
        medium: "#eab308",
        low: "#3b82f6",
        pass: "#22c55e",
        fail: "#ef4444",
        warn: "#eab308",
        upcoming: "#8b5cf6",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
