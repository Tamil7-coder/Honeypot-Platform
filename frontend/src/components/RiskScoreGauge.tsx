function scoreColor(score: number): string {
  if (score >= 70) return "#f43f5e";
  if (score >= 40) return "#fb923c";
  if (score >= 10) return "#f59e0b";
  return "#34d399";
}

function scoreLabel(score: number): string {
  if (score >= 70) return "CRITICAL";
  if (score >= 40) return "HIGH";
  if (score >= 10) return "MEDIUM";
  return "LOW";
}

export default function RiskScoreGauge({ score, sampleSize }: { score: number; sampleSize: number }) {
  const color = scoreColor(score);
  const clamped = Math.min(100, Math.max(0, score));

  // Semicircle gauge: 180deg arc, stroke-dasharray trick
  const radius = 54;
  const circumference = Math.PI * radius;
  const filled = (clamped / 100) * circumference;

  return (
    <div className="flex flex-col items-center py-2">
      <svg viewBox="0 0 140 80" width="180" height="105">
        <path
          d="M 16 70 A 54 54 0 0 1 124 70"
          fill="none"
          stroke="#232a38"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <path
          d="M 16 70 A 54 54 0 0 1 124 70"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
        <text x="70" y="60" textAnchor="middle" fontSize="24" fontWeight="700" fill={color} fontFamily="monospace">
          {Math.round(score)}
        </text>
      </svg>
      <p className="text-xs font-semibold uppercase tracking-wide mt-1" style={{ color }}>
        {scoreLabel(score)}
      </p>
      <p className="text-[10px] text-soc-textFaint mt-1">
        Avg. of {sampleSize} session{sampleSize === 1 ? "" : "s"} (24h)
      </p>
    </div>
  );
}
