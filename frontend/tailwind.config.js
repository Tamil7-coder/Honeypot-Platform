/** @type {import('tailwindcss').Config} */

// Wires a Tailwind color token to a CSS custom property (defined per-theme
// in src/index.css), so `bg-soc-bg`, `text-soc-cyan`, etc. automatically
// repaint when the `light` class toggles on <html> -- no per-component
// theme logic required. Tailwind's opacity modifiers (e.g. bg-soc-bg/50)
// keep working via the <alpha-value> placeholder.
function themedColor(cssVar) {
  return `rgb(var(${cssVar}) / <alpha-value>)`;
}

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        soc: {
          bg: themedColor("--soc-bg"),
          bgElevated: themedColor("--soc-bg-elevated"),
          panel: themedColor("--soc-panel"),
          panelSolid: themedColor("--soc-panel-solid"),
          panelBorder: themedColor("--soc-panel-border"),
          panelBorderHover: themedColor("--soc-panel-border-hover"),
          cyan: themedColor("--soc-cyan"),
          indigo: themedColor("--soc-indigo"),
          danger: themedColor("--soc-danger"),
          warning: themedColor("--soc-warning"),
          success: themedColor("--soc-success"),
          textMuted: themedColor("--soc-text-muted"),
          textFaint: themedColor("--soc-text-faint"),
          textPrimary: themedColor("--soc-text-primary"),
        },
      },
      fontFamily: {
        display: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        "signature-gradient": "linear-gradient(135deg, #22d3ee 0%, #6366f1 100%)",
        "glow-radial": "radial-gradient(circle at center, rgba(34,211,238,0.15) 0%, transparent 70%)",
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)",
        "glow-cyan": "0 0 24px rgba(34,211,238,0.25)",
      },
      animation: {
        "spin-slow": "spin 8s linear infinite",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "fade-up": "fadeUp 0.4s ease-out both",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: 0, transform: "translateY(8px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
