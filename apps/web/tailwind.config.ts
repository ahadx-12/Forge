import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0B0F19",
          800: "#101827",
          700: "#1B2433",
        },
        frost: {
          100: "#EEF4FF",
          200: "#D9E5FF",
        },
        accent: {
          400: "#7C9DFF",
          500: "#5A78FF",
          600: "#3D56F3",
        },
      },
      boxShadow: {
        glow: "0 0 32px rgba(90, 120, 255, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
