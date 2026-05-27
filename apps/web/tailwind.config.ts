import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1280px" },
    },
    extend: {
      colors: {
        // Brand palette — ivory + navy + gold
        ivory: {
          DEFAULT: "#F8F4EC",
          50: "#FCFAF5",
          100: "#F8F4EC",
          200: "#F1EADC",
          300: "#E6DBC5",
        },
        navy: {
          DEFAULT: "#0B1B2B",
          50: "#E6E8EB",
          100: "#9FA6AF",
          500: "#1B324A",
          900: "#0B1B2B",
        },
        gold: {
          DEFAULT: "#C8A24B",
          50: "#FAF3DE",
          100: "#EFDDA7",
          400: "#D8B564",
          500: "#C8A24B",
          600: "#A8862F",
        },
        // shadcn-compatible aliases
        background: "#F8F4EC",
        foreground: "#0B1B2B",
        primary: { DEFAULT: "#0B1B2B", foreground: "#F8F4EC" },
        accent: { DEFAULT: "#C8A24B", foreground: "#0B1B2B" },
        muted: { DEFAULT: "#F1EADC", foreground: "#5E6873" },
        border: "#E6DBC5",
        ring: "#C8A24B",
      },
      fontFamily: {
        arabic: ["var(--font-arabic)", "Tajawal", "IBM Plex Sans Arabic", "sans-serif"],
        display: ["var(--font-display)", "var(--font-arabic)", "serif"],
      },
      borderRadius: {
        lg: "12px",
        md: "8px",
        sm: "6px",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 220ms ease-out",
        "slide-up": "slide-up 260ms ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
