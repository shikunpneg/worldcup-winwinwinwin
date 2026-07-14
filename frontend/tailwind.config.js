/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1a2e",
        "bg-light": "#1a2d4a",
        "box-future": "#2a1a3a",
        line: "#4a6fa5",
        accent: "#f0c040",
        "accent-dim": "#b8860b",
      },
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
