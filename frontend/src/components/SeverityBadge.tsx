export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

const SEVERITY_STYLES: Record<Severity, string> = {
  LOW: "bg-soc-success/10 text-soc-success ring-soc-success/30",
  MEDIUM: "bg-soc-warning/10 text-soc-warning ring-soc-warning/30",
  HIGH: "bg-orange-500/10 text-orange-400 ring-orange-500/30",
  CRITICAL: "bg-soc-danger/10 text-soc-danger ring-soc-danger/30",
};

/**
 * Renders a colored severity badge. Returns null if no severity is provided —
 * the Risk Scoring Engine (Phase 7) is what populates this value; until then,
 * callers simply don't pass a severity rather than this component faking one.
 */
export default function SeverityBadge({ severity }: { severity?: Severity | null }) {
  if (!severity) return null;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold tracking-wide ring-1 ${SEVERITY_STYLES[severity]}`}
    >
      {severity}
    </span>
  );
}
