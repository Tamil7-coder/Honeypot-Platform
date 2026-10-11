import { ReactNode } from "react";
import { motion } from "framer-motion";
import { Radar } from "lucide-react";

export default function AuthCard({
  subtitle,
  children,
}: {
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="relative flex h-screen items-center justify-center overflow-hidden bg-soc-bg">
      <div className="pointer-events-none absolute -top-32 -right-32 h-[520px] w-[520px] rounded-full bg-glow-radial" />
      <div className="pointer-events-none absolute -bottom-40 -left-40 h-[420px] w-[420px] rounded-full bg-glow-radial" />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative w-full max-w-sm rounded-2xl border border-soc-panelBorder glass-panel p-8 shadow-glass"
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="relative">
            <div className="absolute inset-0 animate-spin-slow rounded-full bg-signature-gradient opacity-40 blur-md" />
            <div className="relative rounded-full bg-soc-bgElevated p-2.5 ring-1 ring-soc-panelBorder">
              <Radar size={20} className="text-soc-cyan" />
            </div>
          </div>
          <div>
            <h1 className="text-slate-100 text-base font-semibold tracking-widest">HONEYNET SOC</h1>
            <p className="text-soc-textFaint text-xs">Attack Analytics Platform</p>
          </div>
        </div>

        <p className="text-soc-textMuted text-xs mb-6">{subtitle}</p>

        {children}
      </motion.div>
    </div>
  );
}
