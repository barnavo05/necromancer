import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F6F4EE",
        ink: "#111310",
        muted: "#5E625B",
        line: "#DAD6CB",
        phosphor: "#2BD46B",
        screen: "#0A0E0B",
      },
      fontFamily: {
        sans: ["Helvetica Neue", "Helvetica", "Arial", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: { rise: "rise 900ms cubic-bezier(0.22, 1, 0.36, 1) both" },
    },
  },
  plugins: [],
};
export default config;
