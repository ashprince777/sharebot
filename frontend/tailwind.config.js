/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#090d16",       // Deep trading terminal black/slate
        surface: "#0f172a",          // Dark navy slate card bg
        border: "#1e293b",           // Slate border
        primary: {
          DEFAULT: "#0ea5e9",        // Electric light blue
          hover: "#0284c7",
        },
        bullish: {
          DEFAULT: "#10b981",        // Emerald green
          glow: "rgba(16, 185, 129, 0.15)",
        },
        bearish: {
          DEFAULT: "#f43f5e",        // Crimson rose/pink
          glow: "rgba(244, 63, 94, 0.15)",
        },
        accent: "#a855f7",           // Purple highlights
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
    },
  },
  plugins: [],
}
