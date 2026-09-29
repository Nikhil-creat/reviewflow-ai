import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { void: "#05060f", panel: "#0b0d1c", neon: { cyan: "#22d3ee", violet: "#a78bfa", pink: "#f472b6", lime: "#a3e635", amber: "#fbbf24" } },
      fontFamily: { mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"] },
      keyframes: {
        float: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-14px)" } },
        scan: { "0%": { transform: "translateY(-100%)" }, "100%": { transform: "translateY(100%)" } },
        shimmer: { "0%": { backgroundPosition: "0% 50%" }, "100%": { backgroundPosition: "200% 50%" } },
      },
      animation: { float: "float 7s ease-in-out infinite", scan: "scan 6s linear infinite", shimmer: "shimmer 6s linear infinite" },
    },
  },
  plugins: [],
};
export default config;
