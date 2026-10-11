import { ReactNode } from "react";
import { motion } from "framer-motion";

interface PanelProps {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  delay?: number;
  className?: string;
}

export default function Panel({ title, children, action, delay = 0, className = "" }: PanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className={`rounded-xl border border-soc-panelBorder glass-panel p-5 shadow-glass ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">{title}</h2>
        {action}
      </div>
      {children}
    </motion.div>
  );
}
