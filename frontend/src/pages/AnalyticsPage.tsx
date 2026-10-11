import { useQuery } from "@tanstack/react-query";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Line, Doughnut } from "react-chartjs-2";
import { Clock, Timer } from "lucide-react";
import { fetchAdvancedAnalytics } from "../api/endpoints";
import Panel from "../components/Panel";
import StatCard from "../components/StatCard";
import AttackHeatmap from "../components/AttackHeatmap";
import { SkeletonBlock, SkeletonCard } from "../components/Skeleton";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Tooltip, Legend);

const GRID_COLOR = "#232a38";
const TEXT_COLOR = "#8b96a8";

const chartOptions = {
  responsive: true,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR } },
    y: { grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR } },
  },
};

const SEVERITY_COLORS: Record<string, string> = {
  low: "#34d399",
  medium: "#f59e0b",
  high: "#fb923c",
  critical: "#f43f5e",
  unclassified: "#5b6579",
};

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

export default function AnalyticsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["advanced-analytics"],
    queryFn: fetchAdvancedAnalytics,
    refetchInterval: 60_000,
  });

  if (error) {
    return <div className="p-8 text-soc-danger">Failed to load analytics.</div>;
  }

  const hourlyData = {
    labels: data?.hourly_distribution.map((h) => `${h.hour}:00`) ?? [],
    datasets: [
      {
        data: data?.hourly_distribution.map((h) => h.attack_count) ?? [],
        backgroundColor: "#22d3ee",
        borderRadius: 3,
      },
    ],
  };

  const weeklyData = {
    labels: data?.weekly_trend.map((w) => w.week) ?? [],
    datasets: [
      {
        data: data?.weekly_trend.map((w) => w.attack_count) ?? [],
        borderColor: "#6366f1",
        backgroundColor: "#6366f122",
        tension: 0.3,
        fill: true,
      },
    ],
  };

  const monthlyData = {
    labels: data?.monthly_trend.map((m) => m.month) ?? [],
    datasets: [
      {
        data: data?.monthly_trend.map((m) => m.attack_count) ?? [],
        backgroundColor: "#22d3ee",
        borderRadius: 3,
      },
    ],
  };

  const riskData = {
    labels: data?.risk_distribution.map((r) => r.severity.toUpperCase()) ?? [],
    datasets: [
      {
        data: data?.risk_distribution.map((r) => r.attack_count) ?? [],
        backgroundColor: data?.risk_distribution.map((r) => SEVERITY_COLORS[r.severity] ?? "#5b6579") ?? [],
        borderWidth: 0,
      },
    ],
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Attack Analytics</h1>
        <p className="text-soc-textMuted text-sm">Deep-dive patterns across time, commands, and risk.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {isLoading || !data ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard
              label="Avg Session Duration"
              value={formatDuration(data.session_duration.avg_seconds)}
              icon={Clock}
              accent="cyan"
            />
            <StatCard
              label="Median Duration"
              value={formatDuration(data.session_duration.median_seconds)}
              icon={Timer}
              accent="indigo"
            />
            <StatCard
              label="Longest Session"
              value={formatDuration(data.session_duration.max_seconds)}
              icon={Clock}
              accent="warning"
            />
            <StatCard
              label="Shortest Session"
              value={formatDuration(data.session_duration.min_seconds)}
              icon={Clock}
              accent="success"
            />
          </>
        )}
      </div>

      <Panel title="Attack Heatmap (Day × Hour)">
        {isLoading || !data ? <SkeletonBlock className="h-48" /> : <AttackHeatmap data={data.attack_heatmap} />}
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Hourly Distribution">
          {isLoading || !data ? <SkeletonBlock className="h-64" /> : <Bar data={hourlyData} options={chartOptions} />}
        </Panel>
        <Panel title="Risk Distribution">
          {isLoading || !data ? (
            <SkeletonBlock className="h-64" />
          ) : data.risk_distribution.length === 0 ? (
            <p className="text-sm text-soc-textMuted text-center py-16">No classified sessions yet.</p>
          ) : (
            <div className="max-w-[280px] mx-auto">
              <Doughnut
                data={riskData}
                options={{
                  plugins: {
                    legend: {
                      position: "bottom" as const,
                      labels: { color: TEXT_COLOR, boxWidth: 10, font: { size: 11 } },
                    },
                  },
                }}
              />
            </div>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Weekly Trend (8 Weeks)">
          {isLoading || !data ? (
            <SkeletonBlock className="h-56" />
          ) : (
            <Line data={weeklyData} options={chartOptions} />
          )}
        </Panel>
        <Panel title="Monthly Trend (6 Months)">
          {isLoading || !data ? (
            <SkeletonBlock className="h-56" />
          ) : (
            <Bar data={monthlyData} options={chartOptions} />
          )}
        </Panel>
      </div>

      <Panel title="Top Commands Executed">
        {isLoading || !data ? (
          <SkeletonBlock className="h-32" />
        ) : data.top_commands.length === 0 ? (
          <p className="text-sm text-soc-textMuted text-center py-6">No commands captured yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-soc-textMuted border-b border-soc-panelBorder">
                <th className="py-2 font-medium">Command</th>
                <th className="py-2 font-medium">Executions</th>
              </tr>
            </thead>
            <tbody>
              {data.top_commands.map((c, i) => (
                <tr key={i} className="border-b border-soc-panelBorder/50">
                  <td className="py-2 text-slate-200 font-mono text-xs truncate max-w-md">{c.command}</td>
                  <td className="py-2 text-soc-danger font-mono">{c.execution_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
