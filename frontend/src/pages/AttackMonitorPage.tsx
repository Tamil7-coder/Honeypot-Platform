import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, Link } from "react-router-dom";
import { SlidersHorizontal, Radio, X, RotateCcw } from "lucide-react";
import { fetchAttackSessions, AttackSearchFilters } from "../api/endpoints";
import Panel from "../components/Panel";
import { SkeletonRow } from "../components/Skeleton";
import SeverityBadge, { Severity } from "../components/SeverityBadge";
import ThreatIntelPanel from "../components/ThreatIntelPanel";

const EMPTY_FILTERS: AttackSearchFilters = {};

export default function AttackMonitorPage() {
  const [searchParams] = useSearchParams();
  const initialIp = searchParams.get("ip") ?? "";

  const [draft, setDraft] = useState<AttackSearchFilters>({ source_ip: initialIp || undefined });
  const [applied, setApplied] = useState<AttackSearchFilters>({ source_ip: initialIp || undefined });
  const [showFilters, setShowFilters] = useState(!!initialIp);
  const [selectedIp, setSelectedIp] = useState<string | null>(null);

  const activeFilterCount = Object.values(applied).filter(Boolean).length;

  const { data, isLoading, error } = useQuery({
    queryKey: ["attack-sessions", applied],
    queryFn: () => fetchAttackSessions(0, 100, applied),
    refetchInterval: 10_000,
  });

  function updateDraft(field: keyof AttackSearchFilters, value: string) {
    setDraft((prev) => ({ ...prev, [field]: value || undefined }));
  }

  function applyFilters() {
    setApplied(draft);
  }

  function clearFilters() {
    setDraft(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
            Live Attack Monitor
            <Radio size={14} className="text-soc-cyan animate-pulse-slow" />
          </h1>
          <p className="text-soc-textMuted text-sm">Recent honeypot sessions across all sensors.</p>
        </div>

        <button
          onClick={() => setShowFilters((v) => !v)}
          className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
            showFilters || activeFilterCount > 0
              ? "border-soc-cyan/50 text-soc-cyan bg-soc-cyan/10"
              : "border-soc-panelBorder text-soc-textMuted hover:text-slate-100"
          }`}
        >
          <SlidersHorizontal size={13} />
          Advanced Search
          {activeFilterCount > 0 && (
            <span className="rounded-full bg-soc-cyan text-black px-1.5 text-[10px] font-bold">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {showFilters && (
        <Panel title="Search Filters">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Field label="Source IP" value={draft.source_ip} onChange={(v) => updateDraft("source_ip", v)} placeholder="e.g. 192.168" />
            <Field label="Country Code" value={draft.country_code} onChange={(v) => updateDraft("country_code", v)} placeholder="e.g. US" />

            <div>
              <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">Protocol</label>
              <select
                value={draft.protocol ?? ""}
                onChange={(e) => updateDraft("protocol", e.target.value)}
                className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2 px-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60"
              >
                <option value="">Any</option>
                <option value="ssh">SSH</option>
                <option value="telnet">Telnet</option>
                <option value="http">HTTP</option>
                <option value="ftp">FTP</option>
                <option value="smb">SMB</option>
                <option value="rdp">RDP</option>
                <option value="dns">DNS</option>
                <option value="smtp">SMTP</option>
                <option value="mqtt">MQTT</option>
                <option value="mysql">MySQL</option>
                <option value="mssql">MSSQL</option>
                <option value="postgresql">PostgreSQL</option>
                <option value="modbus">Modbus/ICS</option>
              </select>
            </div>
            <Field label="Username" value={draft.username} onChange={(v) => updateDraft("username", v)} placeholder="e.g. root" />
            <Field label="Password" value={draft.password} onChange={(v) => updateDraft("password", v)} placeholder="e.g. admin" />
            <Field label="Command" value={draft.command} onChange={(v) => updateDraft("command", v)} placeholder="e.g. wget" />
            <Field label="Session Ref" value={draft.session_ref} onChange={(v) => updateDraft("session_ref", v)} placeholder="e.g. cowrie-" />

            <div>
              <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">Severity</label>
              <select
                value={draft.severity ?? ""}
                onChange={(e) => updateDraft("severity", e.target.value)}
                className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2 px-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60"
              >
                <option value="">Any</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">Date From</label>
              <input
                type="date"
                value={draft.date_from?.slice(0, 10) ?? ""}
                onChange={(e) => updateDraft("date_from", e.target.value ? `${e.target.value}T00:00:00Z` : "")}
                className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2 px-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60"
              />
            </div>
            <div>
              <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">Date To</label>
              <input
                type="date"
                value={draft.date_to?.slice(0, 10) ?? ""}
                onChange={(e) => updateDraft("date_to", e.target.value ? `${e.target.value}T23:59:59Z` : "")}
                className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2 px-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 mt-5">
            <button
              onClick={applyFilters}
              className="rounded-lg bg-signature-gradient px-4 py-2 text-xs font-semibold text-black hover:opacity-90 transition-opacity"
            >
              Apply Filters
            </button>
            <button
              onClick={clearFilters}
              className="flex items-center gap-1.5 rounded-lg border border-soc-panelBorder px-3 py-2 text-xs text-soc-textMuted hover:text-slate-100"
            >
              <RotateCcw size={12} /> Clear All
            </button>
          </div>
        </Panel>
      )}

      <Panel
        title={`Sessions ${data ? `(${data.total} total)` : ""}`}
        action={
          activeFilterCount > 0 ? (
            <button onClick={clearFilters} className="flex items-center gap-1 text-[10px] text-soc-textMuted hover:text-slate-100">
              <X size={11} /> Clear filters
            </button>
          ) : undefined
        }
      >
        {error && <p className="text-soc-danger text-sm">Failed to load sessions.</p>}

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-soc-textMuted border-b border-soc-panelBorder">
              <th className="py-2 font-medium">Severity</th>
              <th className="py-2 font-medium">Source IP</th>
              <th className="py-2 font-medium">Protocol</th>
              <th className="py-2 font-medium">Country</th>
              <th className="py-2 font-medium">Started</th>
              <th className="py-2 font-medium">Duration</th>
              <th className="py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={7} />)}
            {!isLoading &&
              data?.items.map((session) => (
                <tr key={session.id} className="border-b border-soc-panelBorder/50 hover:bg-white/[0.02]">
                  <td className="py-2.5">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={session.severity?.toUpperCase() as Severity | undefined} />
                      {session.risk_score !== null && (
                        <span className="text-[10px] text-soc-textFaint font-mono">{session.risk_score}</span>
                      )}
                    </div>
                  </td>
                  <td className="py-2.5 text-slate-200 font-mono">
                    <button
                      onClick={() => setSelectedIp(session.source_ip)}
                      className="hover:text-soc-cyan hover:underline transition-colors"
                      title="View threat intelligence"
                    >
                      {session.source_ip}
                    </button>
                  </td>
                  <td className="py-2.5 uppercase text-soc-cyan font-mono text-xs">{session.protocol}</td>
                  <td className="py-2.5 text-slate-400">{session.country_code ?? "—"}</td>
                  <td className="py-2.5 text-slate-400">{new Date(session.started_at).toLocaleString()}</td>
                  <td className="py-2.5 text-slate-400 font-mono">
                    {session.duration_seconds != null ? `${session.duration_seconds}s` : "—"}
                  </td>
                  <td className="py-2.5 text-right">
                    <Link
                      to={`/attacks/${session.id}/replay`}
                      className="text-[10px] uppercase tracking-wide text-soc-cyan hover:underline"
                    >
                      Replay
                    </Link>
                  </td>
                </tr>
              ))}
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={7} className="py-6 text-center text-soc-textMuted">
                  {activeFilterCount > 0 ? "No sessions match these filters." : "No sessions captured yet."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>

      {selectedIp && <ThreatIntelPanel ip={selectedIp} onClose={() => setSelectedIp(null)} />}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value?: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">{label}</label>
      <input
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2 px-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60 focus:ring-1 focus:ring-soc-cyan/30"
      />
    </div>
  );
}
