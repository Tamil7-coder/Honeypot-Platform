import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Line, Bar } from "react-chartjs-2";
import {
  Crosshair,
  Server,
  Activity,
  ShieldAlert,
  CalendarClock,
  Gauge,
  Radio,
  Bell,
  ShieldCheck,
  ListChecks,
} from "lucide-react";
import { fetchDashboardSummary } from "../api/endpoints";
import { useLiveFeed } from "../context/LiveFeedContext";
import StatCard from "../components/StatCard";
import Panel from "../components/Panel";
import ComingSoonWidget from "../components/ComingSoonWidget";
import RiskScoreGauge from "../components/RiskScoreGauge";
import SeverityBadge, { Severity } from "../components/SeverityBadge";
import { SkeletonCard, SkeletonBlock, SkeletonRow } from "../components/Skeleton";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend);

const CHART_GRID_COLOR = "#232a38";
const CHART_TEXT_COLOR = "#8b96a8";

const chartOptions = {
  responsive: true,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { color: CHART_GRID_COLOR }, ticks: { color: CHART_TEXT_COLOR } },
    y: { grid: { color: CHART_GRID_COLOR }, ticks: { color: CHART_TEXT_COLOR } },
  },
};

export default function DashboardPage() {
  const { events: liveEvents, isConnected } = useLiveFeed();
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: fetchDashboardSummary,
    // WebSocket events (Phase 4) drive instant refetches on every new
    // attack/alert; this interval is just a resilience fallback in case the
    // live connection is temporarily down.
    refetchInterval: 60_000,
  });

  if (error) {
    return <div className="p-8 text-soc-danger">Failed to load dashboard data.</div>;
  }

  const trendData = {
    labels: data?.attacks_last_7_days.map((d) => d.day) ?? [],
    datasets: [
      {
        label: "Attacks",
        data: data?.attacks_last_7_days.map((d) => d.attack_count) ?? [],
        borderColor: "#22d3ee",
        backgroundColor: "#22d3ee22",
        tension: 0.35,
        fill: true,
      },
    ],
  };

  const servicesData = {
    labels: data?.top_targeted_services.map((s) => s.protocol.toUpperCase()) ?? [],
    datasets: [
      {
        label: "Attacks",
        data: data?.top_targeted_services.map((s) => s.attack_count) ?? [],
        backgroundColor: "#6366f1",
        borderRadius: 4,
      },
    ],
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Security Operations Overview</h1>
          <p className="text-soc-textMuted text-sm">Live honeypot attack analytics, refreshed every 15s.</p>
        </div>
        <Link
          to="/attacks"
          className="hidden sm:flex items-center gap-1.5 rounded-lg border border-soc-panelBorder bg-white/5 px-3 py-1.5 text-xs text-soc-textMuted hover:text-slate-100 hover:border-soc-panelBorderHover transition-colors"
        >
          <Radio size={13} className="text-soc-cyan animate-pulse-slow" />
          Live Attack Monitor
        </Link>
      </div>

      {/* Row 1 — primary counters */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {isLoading || !data ? (
          Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard label="Total Attacks" value={data.total_attacks} icon={Crosshair} accent="cyan" delay={0} />
            <StatCard
              label="Active Honeypots"
              value={`${data.active_honeypots}/${data.total_honeypots}`}
              icon={Server}
              accent="indigo"
              delay={0.05}
            />
            <StatCard
              label="Active Sessions"
              value={data.active_sessions_last_hour}
              icon={Activity}
              accent="warning"
              subtext="last hour"
              delay={0.1}
            />
            <StatCard
              label="Today's Attacks"
              value={data.attacks_today}
              icon={CalendarClock}
              accent="success"
              delay={0.15}
            />
            <StatCard
              label="Unique Attacker IPs"
              value={data.unique_attacker_ips}
              icon={ShieldAlert}
              accent="danger"
              delay={0.2}
            />
          </>
        )}
      </div>

      {/* Live Attack Feed — pushed instantly via WebSocket, not polled */}
      <Panel
        title="Live Attack Feed"
        delay={0.05}
        action={
          <span className={`text-[10px] uppercase tracking-wide ${isConnected ? "text-soc-success" : "text-soc-textFaint"}`}>
            {isConnected ? "● streaming" : "○ reconnecting"}
          </span>
        }
      >
        {liveEvents.filter((e) => e.type === "new_attack").length === 0 ? (
          <p className="text-sm text-soc-textMuted text-center py-6">
            Waiting for live traffic — new sessions will appear here instantly.
          </p>
        ) : (
          <ul className="space-y-1.5 max-h-48 overflow-y-auto pr-1 font-mono text-xs">
            {liveEvents
              .filter((e) => e.type === "new_attack")
              .slice(0, 12)
              .map((event) => {
                const d = event.data as { source_ip: string; protocol: string; severity: string | null };
                return (
                  <li key={event.key} className="flex items-center gap-3 text-slate-300 animate-fade-up">
                    <span className="text-soc-textFaint">{new Date(event.receivedAt).toLocaleTimeString()}</span>
                    <span className="text-soc-cyan uppercase">{d.protocol}</span>
                    <span>{d.source_ip}</span>
                    {d.severity && <SeverityBadge severity={d.severity.toUpperCase() as Severity} />}
                  </li>
                );
              })}
          </ul>
        )}
      </Panel>

      {/* Row 2 — charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Attack Timeline (7 Days)" delay={0.1}>
          {isLoading || !data ? <SkeletonBlock className="h-64" /> : <Line data={trendData} options={chartOptions} />}
        </Panel>
        <Panel title="Most Targeted Services" delay={0.15}>
          {isLoading || !data ? (
            <SkeletonBlock className="h-64" />
          ) : (
            <Bar data={servicesData} options={chartOptions} />
          )}
        </Panel>
      </div>

      {/* Row 3 — risk & alerts (future phases) + honeypot status (real) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel title="Risk Score" delay={0.1}>
          {isLoading || !data ? (
            <SkeletonBlock className="h-32" />
          ) : data.avg_risk_score_24h === null ? (
            <ComingSoonWidget icon={Gauge} title="No scored sessions yet" phaseLabel="the next attack" />
          ) : (
            <RiskScoreGauge score={data.avg_risk_score_24h} sampleSize={data.risk_score_sample_size} />
          )}
        </Panel>
        <Panel title="Recent Alerts" delay={0.15}>
          {isLoading || !data ? (
            <SkeletonBlock className="h-32" />
          ) : data.recent_alerts.length === 0 ? (
            <ComingSoonWidget icon={Bell} title="No alerts yet" phaseLabel="HIGH/CRITICAL sessions" />
          ) : (
            <ul className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
              {data.recent_alerts.map((alert) => (
                <li key={alert.id} className="flex items-start justify-between gap-3 text-sm">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <SeverityBadge severity={alert.severity.toUpperCase() as Severity} />
                      <span className="text-soc-textFaint text-[10px]">
                        {new Date(alert.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-slate-300 text-xs truncate" title={alert.message}>
                      {alert.message}
                    </p>
                  </div>
                  {!alert.email_sent && (
                    <span className="shrink-0 text-[10px] text-soc-textFaint" title="Email not delivered">
                      no email
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Honeypot Status" delay={0.2}>
          {isLoading || !data ? (
            <SkeletonBlock className="h-32" />
          ) : (
            <ul className="space-y-2">
              {data.honeypot_status.map((h) => (
                <li key={h.name} className="flex items-center justify-between text-sm py-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${h.is_active ? "bg-soc-success" : "bg-soc-textFaint"}`}
                    />
                    <span className="text-slate-200">{h.name}</span>
                    <span className="text-soc-textFaint uppercase text-xs">{h.type}</span>
                  </div>
                  <span className="text-soc-textMuted text-xs font-mono">{h.session_count} sessions</span>
                </li>
              ))}
              {data.honeypot_status.length === 0 && (
                <p className="text-soc-textMuted text-sm text-center py-6">No honeypots registered yet.</p>
              )}
            </ul>
          )}
        </Panel>
      </div>

      {/* Row 4 — attribution tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel title="Top Attacking Countries" delay={0.1}>
          <SimpleTable
            isLoading={isLoading}
            rows={data?.top_countries.map((c) => [c.country_code, String(c.attack_count)]) ?? []}
            headers={["Country", "Attacks"]}
            emptyLabel="No country data yet."
          />
        </Panel>
        <Panel title="Top Attacker IPs" delay={0.15}>
          <SimpleTable
            isLoading={isLoading}
            rows={data?.top_attacker_ips.map((ip) => [ip.source_ip, String(ip.attack_count)]) ?? []}
            headers={["Source IP", "Attacks"]}
            emptyLabel="No attack data yet — waiting on honeypot traffic."
            valueClassName="text-soc-danger"
          />
        </Panel>
        <Panel title="Most Used Usernames" delay={0.2}>
          <SimpleTable
            isLoading={isLoading}
            rows={data?.top_usernames.map((u) => [u.username, String(u.attempt_count)]) ?? []}
            headers={["Username", "Attempts"]}
            emptyLabel="No login attempts yet."
          />
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel title="Most Used Passwords" delay={0.1}>
          <SimpleTable
            isLoading={isLoading}
            rows={data?.top_passwords.map((p) => [p.password, String(p.attempt_count)]) ?? []}
            headers={["Password", "Attempts"]}
            emptyLabel="No login attempts yet."
          />
        </Panel>

        <Panel title="Quick Actions" delay={0.15} className="lg:col-span-2">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <QuickAction to="/attacks" icon={ShieldAlert} label="Investigate Live Attacks" />
            <QuickAction to="/settings" icon={ShieldCheck} label="Review Account Settings" />
            <QuickAction to="/attacks" icon={ListChecks} label="Browse Session History" />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function SimpleTable({
  isLoading,
  rows,
  headers,
  emptyLabel,
  valueClassName = "text-slate-200",
}: {
  isLoading: boolean;
  rows: string[][];
  headers: [string, string];
  emptyLabel: string;
  valueClassName?: string;
}) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-soc-textMuted border-b border-soc-panelBorder">
          <th className="py-2 font-medium">{headers[0]}</th>
          <th className="py-2 font-medium">{headers[1]}</th>
        </tr>
      </thead>
      <tbody>
        {isLoading &&
          Array.from({ length: 3 }).map((_, i) => <SkeletonRow key={i} cols={2} />)}
        {!isLoading &&
          rows.map(([label, count], i) => (
            <tr key={`${label}-${i}`} className="border-b border-soc-panelBorder/50">
              <td className="py-2 text-slate-200 font-mono">{label}</td>
              <td className={`py-2 font-mono ${valueClassName}`}>{count}</td>
            </tr>
          ))}
        {!isLoading && rows.length === 0 && (
          <tr>
            <td colSpan={2} className="py-4 text-center text-soc-textMuted">
              {emptyLabel}
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

function QuickAction({ to, icon: Icon, label }: { to: string; icon: typeof ShieldAlert; label: string }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 rounded-lg border border-soc-panelBorder bg-white/5 px-4 py-3 text-sm text-slate-200 transition-colors hover:border-soc-cyan/40 hover:bg-white/10"
    >
      <Icon size={16} className="text-soc-cyan shrink-0" />
      {label}
    </Link>
  );
}
