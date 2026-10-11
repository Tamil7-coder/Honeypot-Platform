import { FormEvent, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Mail,
  Bell,
  Clock,
  Trash2,
  Moon,
  Send,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Save,
} from "lucide-react";
import {
  fetchSettings,
  updateSettings,
  runRetentionCleanup,
  sendTestEmail,
  SettingsUpdatePayload,
} from "../api/endpoints";
import Panel from "./Panel";

export default function AdminSettingsPanel() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["platform-settings"], queryFn: fetchSettings });

  const [form, setForm] = useState<SettingsUpdatePayload | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [testEmailTo, setTestEmailTo] = useState("");
  const [testEmailStatus, setTestEmailStatus] = useState<{ success: boolean; detail: string } | null>(null);
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<string | null>(null);
  const [isCleaning, setIsCleaning] = useState(false);

  const current = form ?? data;

  function update<K extends keyof SettingsUpdatePayload>(field: K, value: SettingsUpdatePayload[K]) {
    setForm((prev) => ({ ...(prev ?? data), [field]: value }));
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaveStatus("saving");
    try {
      await updateSettings(form);
      await queryClient.invalidateQueries({ queryKey: ["platform-settings"] });
      setForm(null);
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2500);
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  }

  async function handleTestEmail() {
    if (!testEmailTo) return;
    setIsSendingTest(true);
    setTestEmailStatus(null);
    try {
      const result = await sendTestEmail(testEmailTo);
      setTestEmailStatus(result);
    } catch {
      setTestEmailStatus({ success: false, detail: "Request failed." });
    } finally {
      setIsSendingTest(false);
    }
  }

  async function handleCleanup() {
    setIsCleaning(true);
    setCleanupResult(null);
    try {
      const result = await runRetentionCleanup();
      setCleanupResult(
        `Deleted ${result.deleted_sessions} session(s) older than ${result.retention_policy_days} days.`
      );
    } catch {
      setCleanupResult("Cleanup failed.");
    } finally {
      setIsCleaning(false);
    }
  }

  if (isLoading || !current) {
    return (
      <Panel title="Platform Configuration">
        <p className="text-sm text-soc-textMuted">Loading...</p>
      </Panel>
    );
  }

  const isDirty = form !== null;

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <Panel
        title="SMTP Configuration"
        action={
          <label className="flex items-center gap-2 text-xs text-soc-textMuted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={current.email_enabled ?? false}
              onChange={(e) => update("email_enabled", e.target.checked)}
              className="accent-soc-cyan"
            />
            Enabled
          </label>
        }
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TextField label="SMTP Host" value={current.smtp_host} onChange={(v) => update("smtp_host", v)} />
          <TextField
            label="SMTP Port"
            value={String(current.smtp_port ?? "")}
            onChange={(v) => update("smtp_port", Number(v) || 0)}
            type="number"
          />
          <TextField label="Username" value={current.smtp_username} onChange={(v) => update("smtp_username", v)} />
          <TextField
            label={`Password ${data?.smtp_password_configured ? "(configured — leave blank to keep)" : ""}`}
            value={form?.smtp_password ?? ""}
            onChange={(v) => update("smtp_password", v)}
            type="password"
          />
          <TextField
            label="From Email"
            value={current.smtp_from_email}
            onChange={(v) => update("smtp_from_email", v)}
          />
          <TextField label="From Name" value={current.smtp_from_name} onChange={(v) => update("smtp_from_name", v)} />
          <label className="flex items-center gap-2 text-xs text-soc-textMuted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={current.smtp_use_tls ?? true}
              onChange={(e) => update("smtp_use_tls", e.target.checked)}
              className="accent-soc-cyan"
            />
            Use TLS (STARTTLS)
          </label>
        </div>

        <div className="flex items-center gap-3 mt-4 pt-4 border-t border-soc-panelBorder">
          <input
            type="email"
            placeholder="Send test email to..."
            value={testEmailTo}
            onChange={(e) => setTestEmailTo(e.target.value)}
            className="flex-1 max-w-xs rounded-lg border border-soc-panelBorder bg-black/30 py-2 px-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60"
          />
          <button
            type="button"
            onClick={handleTestEmail}
            disabled={isSendingTest || !testEmailTo}
            className="flex items-center gap-1.5 rounded-lg border border-soc-panelBorder px-3 py-2 text-xs text-slate-200 hover:border-soc-cyan/40 disabled:opacity-50"
          >
            {isSendingTest ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
            Send Test
          </button>
          {testEmailStatus && (
            <span className={`text-xs ${testEmailStatus.success ? "text-soc-success" : "text-soc-danger"}`}>
              {testEmailStatus.detail}
            </span>
          )}
        </div>
      </Panel>

      <Panel title="Alerting">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TextField
            label="Admin Alert Email"
            value={current.admin_alert_email}
            onChange={(v) => update("admin_alert_email", v)}
            icon={Mail}
          />
          <div>
            <label className="block text-xs text-soc-textMuted mb-1.5 font-medium flex items-center gap-1.5">
              <Bell size={12} /> Notification Threshold
            </label>
            <select
              value={current.alert_min_severity}
              onChange={(e) => update("alert_min_severity", e.target.value)}
              className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2 px-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60"
            >
              <option value="low">Low and above</option>
              <option value="medium">Medium and above</option>
              <option value="high">High and above</option>
              <option value="critical">Critical only</option>
            </select>
          </div>
        </div>
      </Panel>

      <Panel title="Application Preferences">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-soc-textMuted mb-1.5 font-medium flex items-center gap-1.5">
              <Moon size={12} /> Theme
            </label>
            <div className="rounded-lg border border-soc-panelBorder bg-black/20 py-2 px-3 text-sm text-soc-textMuted">
              Dark (active) — Light theme coming in a future release
            </div>
          </div>
          <TextField
            label="Session Timeout (minutes)"
            value={String(current.session_timeout_minutes ?? "")}
            onChange={(v) => update("session_timeout_minutes", Number(v) || 0)}
            type="number"
            icon={Clock}
          />
          <TextField
            label="Retention Policy (days)"
            value={String(current.retention_policy_days ?? "")}
            onChange={(v) => update("retention_policy_days", Number(v) || 0)}
            type="number"
          />
        </div>

        <div className="flex items-center gap-3 mt-4 pt-4 border-t border-soc-panelBorder">
          <button
            type="button"
            onClick={handleCleanup}
            disabled={isCleaning}
            className="flex items-center gap-1.5 rounded-lg border border-soc-danger/30 text-soc-danger px-3 py-2 text-xs hover:bg-soc-danger/10 disabled:opacity-50"
          >
            {isCleaning ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
            Run Cleanup Now
          </button>
          {cleanupResult && <span className="text-xs text-soc-textMuted">{cleanupResult}</span>}
        </div>
      </Panel>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={!isDirty || saveStatus === "saving"}
          className="flex items-center gap-2 rounded-lg bg-signature-gradient px-5 py-2.5 text-sm font-semibold text-black hover:opacity-90 disabled:opacity-40 transition-opacity"
        >
          {saveStatus === "saving" ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Save Changes
        </button>
        {saveStatus === "saved" && (
          <span className="flex items-center gap-1.5 text-sm text-soc-success">
            <CheckCircle2 size={14} /> Saved
          </span>
        )}
        {saveStatus === "error" && (
          <span className="flex items-center gap-1.5 text-sm text-soc-danger">
            <AlertCircle size={14} /> Failed to save
          </span>
        )}
      </div>
    </form>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
  icon: Icon,
}: {
  label: string;
  value?: string;
  onChange: (v: string) => void;
  type?: string;
  icon?: typeof Mail;
}) {
  return (
    <div>
      <label className="block text-xs text-soc-textMuted mb-1.5 font-medium flex items-center gap-1.5">
        {Icon && <Icon size={12} />} {label}
      </label>
      <input
        type={type}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2 px-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60 focus:ring-1 focus:ring-soc-cyan/30"
      />
    </div>
  );
}
