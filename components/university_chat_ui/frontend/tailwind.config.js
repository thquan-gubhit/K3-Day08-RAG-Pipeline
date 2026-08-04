/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Design tokens — Modern University AI Research Console
        base: { DEFAULT: "#07111F", soft: "#0B1728" },
        card: "rgba(16, 30, 49, 0.78)",
        edge: "rgba(148, 163, 184, 0.14)",
        cyan: { brand: "#22D3EE" },
        indigo: { brand: "#6366F1" },
        violet: { brand: "#A78BFA" },
        ok: "#34D399",
        warn: "#FBBF24",
        danger: "#FB7185",
        ink: "#F8FAFC",
        muted: "#94A3B8",
      },
      fontFamily: {
        sans: [
          "Inter",
          "Segoe UI",
          "system-ui",
          "-apple-system",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
      keyframes: {
        drift: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        drift: "drift 22s ease infinite",
      },
    },
  },
  plugins: [],
};
