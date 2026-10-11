import { Moon, Sun } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

/**
 * Dark/Light theme switch. Dark is the platform default; toggling persists
 * the choice via ThemeContext (localStorage-backed) and smoothly re-themes
 * the whole app since every soc.* color token is CSS-variable driven.
 */
export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isLight = theme === "light";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      role="switch"
      aria-checked={isLight}
      aria-label={`Switch to ${isLight ? "dark" : "light"} theme`}
      title={`Switch to ${isLight ? "dark" : "light"} theme`}
      className="relative inline-flex h-8 w-16 items-center rounded-full border border-soc-panelBorder bg-soc-bgElevated transition-colors duration-300 hover:border-soc-panelBorderHover focus:outline-none focus-visible:ring-2 focus-visible:ring-soc-cyan/50"
    >
      <Moon size={12} className={`absolute left-2 transition-opacity ${isLight ? "opacity-30 text-soc-textFaint" : "opacity-0"}`} />
      <Sun size={12} className={`absolute right-2 transition-opacity ${isLight ? "opacity-0" : "opacity-30 text-soc-textFaint"}`} />
      <span
        className={`absolute inset-y-0.5 left-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-signature-gradient shadow-glow-cyan transition-transform duration-300 ease-in-out ${
          isLight ? "translate-x-8" : "translate-x-0"
        }`}
      >
        {isLight ? <Sun size={14} className="text-white" /> : <Moon size={14} className="text-white" />}
      </span>
    </button>
  );
}
