import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Terminal,
  Download,
  Upload,
  PowerOff,
} from "lucide-react";
import { fetchAttackReplay, ReplayEvent } from "../api/endpoints";
import Panel from "../components/Panel";
import SeverityBadge, { Severity } from "../components/SeverityBadge";
import { SkeletonBlock } from "../components/Skeleton";

const EVENT_META: Record<
  ReplayEvent["event_type"],
  { icon: typeof Terminal; color: string; label: (d: Record<string, unknown>) => string }
> = {
  login_success: {
    icon: CheckCircle2,
    color: "text-soc-success",
    label: (d) => `Login succeeded — ${d.username} / ${d.password}`,
  },
  login_failed: {
    icon: XCircle,
    color: "text-soc-danger",
    label: (d) => `Login failed — ${d.username} / ${d.password}`,
  },
  command: {
    icon: Terminal,
    color: "text-soc-cyan",
    label: (d) => `${d.command_text}`,
  },
  download: {
    icon: Download,
    color: "text-soc-warning",
    label: (d) => `Downloaded ${d.filename ?? d.url ?? "file"}${d.file_size ? ` (${d.file_size} bytes)` : ""}`,
  },
  upload: {
    icon: Upload,
    color: "text-soc-indigo",
    label: (d) => `Uploaded ${d.filename ?? "file"}${d.file_size ? ` (${d.file_size} bytes)` : ""}`,
  },
  disconnect: {
    icon: PowerOff,
    color: "text-soc-textFaint",
    label: () => "Session disconnected",
  },
};

export default function ReplayPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ["attack-replay", sessionId],
    queryFn: () => fetchAttackReplay(sessionId!),
    enabled: !!sessionId,
  });

  const [visibleCount, setVisibleCount] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const timeline = useMemo(() => data?.timeline ?? [], [data]);

  useEffect(() => {
    if (!isPlaying || !data) return;
    if (visibleCount >= timeline.length) {
      setIsPlaying(false);
      return;
    }

    // Pace playback using real inter-event gaps, bounded so a slow attacker
    // doesn't make the replay tediously slow to watch.
    const current = timeline[visibleCount];
    const previous = visibleCount > 0 ? timeline[visibleCount - 1] : null;
    const realGapMs = previous
      ? new Date(current.timestamp).getTime() - new Date(previous.timestamp).getTime()
      : 0;
    const delay = Math.min(Math.max(realGapMs, 300), 1800);

    timerRef.current = setTimeout(() => setVisibleCount((n) => n + 1), delay);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isPlaying, visibleCount, timeline, data]);

  function handlePlayPause() {
    if (visibleCount >= timeline.length) setVisibleCount(0);
    setIsPlaying((p) => !p);
  }

  function handleReset() {
    setIsPlaying(false);
    setVisibleCount(0);
  }

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        <SkeletonBlock className="h-10 w-64" />
        <SkeletonBlock className="h-96" />
      </div>
    );
  }

  if (error || !data) {
    return <div className="p-8 text-soc-danger">Failed to load session replay.</div>;
  }

  const { session } = data;
  const shownCount = isPlaying || visibleCount > 0 ? visibleCount : timeline.length;

  return (
    <div className="p-8 space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-xs text-soc-textMuted hover:text-slate-100"
      >
        <ArrowLeft size={13} /> Back
      </button>

      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100 font-mono">{session.source_ip}</h1>
          <p className="text-soc-textMuted text-sm">
            {session.protocol.toUpperCase()} session · {new Date(session.started_at).toLocaleString()}
            {session.country_code && ` · ${session.country_code}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {session.severity && <SeverityBadge severity={session.severity.toUpperCase() as Severity} />}
          {session.risk_score !== null && (
            <span className="text-xs font-mono text-soc-textMuted">Risk: {session.risk_score}/100</span>
          )}
        </div>
      </div>

      <Panel
        title="Session Replay"
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={handlePlayPause}
              className="flex items-center gap-1.5 rounded-lg bg-signature-gradient px-3 py-1.5 text-xs font-semibold text-black hover:opacity-90 transition-opacity"
            >
              {isPlaying ? <Pause size={12} /> : <Play size={12} />}
              {isPlaying ? "Pause" : visibleCount >= timeline.length ? "Replay" : "Play"}
            </button>
            <button
              onClick={handleReset}
              className="flex items-center gap-1 rounded-lg border border-soc-panelBorder px-2.5 py-1.5 text-xs text-soc-textMuted hover:text-slate-100"
            >
              <RotateCcw size={12} />
            </button>
          </div>
        }
      >
        {timeline.length === 0 ? (
          <p className="text-sm text-soc-textMuted text-center py-10">
            No login attempts, commands, or file transfers captured for this session.
          </p>
        ) : (
          <ol className="relative border-l border-soc-panelBorder ml-3 space-y-5 py-2">
            {timeline.slice(0, shownCount).map((event, i) => {
              const meta = EVENT_META[event.event_type];
              const Icon = meta.icon;
              return (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25 }}
                  className="ml-5 relative"
                >
                  <span
                    className={`absolute -left-[29px] flex h-6 w-6 items-center justify-center rounded-full bg-soc-bgElevated ring-1 ring-soc-panelBorder ${meta.color}`}
                  >
                    <Icon size={13} />
                  </span>
                  <span className="text-[10px] text-soc-textFaint font-mono block">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                  <p
                    className={`text-sm mt-0.5 ${
                      event.event_type === "command" ? "font-mono text-slate-200" : "text-slate-300"
                    }`}
                  >
                    {meta.label(event.detail)}
                  </p>
                  {event.event_type === "command" &&
                    isRecord(event.detail.metadata) &&
                    typeof event.detail.metadata.user_agent === "string" && (
                      <p className="text-[10px] text-soc-textFaint mt-0.5 font-mono truncate">
                        UA: {event.detail.metadata.user_agent}
                      </p>
                    )}
                </motion.li>
              );
            })}
          </ol>
        )}
      </Panel>
    </div>
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
