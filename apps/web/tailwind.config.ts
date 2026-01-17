import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "forge-bg": "#0b0f1a",
        "forge-panel": "#111827",
        "forge-card": "#141c2e",
        "forge-border": "#1f2937",
        "forge-accent": "#7c3aed",
        "forge-accent-soft": "#a78bfa"
      },
      boxShadow: {
        "glow": "0 0 40px rgba(124, 58, 237, 0.25)",
        "panel": "0 12px 30px rgba(2, 6, 23, 0.45)"
      }
    }
  },
  plugins: []
};

export default config;
