const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface HeatmapCell {
  day_of_week: number;
  hour: number;
  attack_count: number;
}

export default function AttackHeatmap({ data }: { data: HeatmapCell[] }) {
  const maxCount = Math.max(1, ...data.map((d) => d.attack_count));
  const lookup = new Map<string, number>();
  data.forEach((d) => lookup.set(`${d.day_of_week}-${d.hour}`, d.attack_count));

  function intensity(count: number): string {
    if (count === 0) return "rgba(255,255,255,0.03)";
    const ratio = count / maxCount;
    return `rgba(34, 211, 238, ${0.15 + ratio * 0.75})`;
  }

  if (data.length === 0) {
    return <p className="text-sm text-soc-textMuted text-center py-10">No attack data yet to build a heatmap.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px]">
        <div className="flex gap-1 mb-1 pl-10">
          {Array.from({ length: 24 }).map((_, hour) => (
            <div key={hour} className="w-5 text-center text-[9px] text-soc-textFaint">
              {hour % 3 === 0 ? hour : ""}
            </div>
          ))}
        </div>
        {DAY_LABELS.map((label, dow) => (
          <div key={dow} className="flex items-center gap-1 mb-1">
            <div className="w-9 text-[10px] text-soc-textMuted text-right pr-1">{label}</div>
            {Array.from({ length: 24 }).map((_, hour) => {
              const count = lookup.get(`${dow}-${hour}`) ?? 0;
              return (
                <div
                  key={hour}
                  title={`${label} ${hour}:00 — ${count} attack(s)`}
                  className="w-5 h-5 rounded-sm"
                  style={{ backgroundColor: intensity(count) }}
                />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
