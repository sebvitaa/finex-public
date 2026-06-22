import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#050505",
        surface: "#0B0B0C",
        surface2: "#111113",
        border: "#242428",
        text: "#F4F4F5",
        muted: "#A1A1AA",
        subtle: "#71717A",
        accent: "#22C55E",
        danger: "#EF4444",
        warning: "#F59E0B",
        info: "#38BDF8"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      boxShadow: {
        panel: "0 18px 60px rgba(0, 0, 0, 0.28)"
      }
    }
  },
  plugins: []
};

export default config;
