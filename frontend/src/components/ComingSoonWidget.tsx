import { LucideIcon } from "lucide-react";

export default function ComingSoonWidget({
  icon: Icon,
  title,
  phaseLabel,
}: {
  icon: LucideIcon;
  title: string;
  phaseLabel: string;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 py-8 text-center">
      <div className="rounded-lg bg-white/5 p-3 ring-1 ring-soc-panelBorder">
        <Icon size={20} className="text-soc-textFaint" />
      </div>
      <p className="text-sm text-soc-textMuted">{title}</p>
      <p className="text-xs text-soc-textFaint">Arriving in {phaseLabel}</p>
    </div>
  );
}
