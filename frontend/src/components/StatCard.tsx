import { ReactNode } from "react";
import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  accent?: "cyan" | "danger" | "warning" | "success" | "indigo";
  subtext?: ReactNode;
  delay?: number;
}

const ACCENT_STYLES: Record<NonNullable<StatCardProps["accent"]>, { text: string; ring: string; glow: string }> = {
  cyan: { text: "text-soc-cyan", ring: "ring-soc-cyan/20", glow: "bg-soc-cyan/10" },
  indigo: { text: "text-soc-indigo", ring: "ring-soc-indigo/20", glow: "bg-soc-indigo/10" },
  danger: { text: "text-soc-danger", ring: "ring-soc-danger/20", glow: "bg-soc-danger/10" },
  warning: { text: "text-soc-warning", ring: "ring-soc-warning/20", glow: "bg-soc-warning/10" },
  success: { text: "text-soc-success", ring: "ring-soc-success/20", glow: "bg-soc-success/10" },
};

export default function StatCard({ label, value, icon: Icon, accent = "cyan", subtext, delay = 0 }: StatCardProps) {
  const styles = ACCENT_STYLES[accent];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className="group relative rounded-xl border border-soc-panelBorder glass-panel px-5 py-4 shadow-glass transition-colors hover:border-soc-panelBorderHover"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-soc-textMuted font-medium">{label}</p>
          <p className={`mt-2 text-2xl font-semibold font-mono ${styles.text}`}>{value}</p>
          {subtext && <p className="mt-1 text-xs text-soc-textFaint">{subtext}</p>}
        </div>
        <div className={`rounded-lg p-2 ring-1 ${styles.ring} ${styles.glow}`}>
          <Icon size={18} className={styles.text} strokeWidth={2} />
        </div>
      </div>
    </motion.div>
  );
}
