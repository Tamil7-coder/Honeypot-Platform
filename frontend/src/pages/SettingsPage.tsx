import { FormEvent, useState } from "react";
import { User, Mail, KeyRound, BadgeCheck, Lock, AlertCircle, CheckCircle2, ShieldAlert } from "lucide-react";
import Panel from "../components/Panel";
import AdminSettingsPanel from "../components/AdminSettingsPanel";
import { useAuth } from "../context/AuthContext";
import { changePassword } from "../api/endpoints";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Settings</h1>
        <p className="text-soc-textMuted text-sm">Account and platform configuration.</p>
      </div>

      <Panel title="Account">
        <dl className="text-sm space-y-1">
          <div className="flex items-center justify-between border-b border-soc-panelBorder/50 py-2.5">
            <dt className="text-soc-textMuted flex items-center gap-2">
              <User size={13} /> Full name
            </dt>
            <dd className="text-slate-200">{user?.full_name}</dd>
          </div>
          <div className="flex items-center justify-between border-b border-soc-panelBorder/50 py-2.5">
            <dt className="text-soc-textMuted flex items-center gap-2">
              <User size={13} /> Username
            </dt>
            <dd className="text-slate-200 font-mono">{user?.username}</dd>
          </div>
          <div className="flex items-center justify-between border-b border-soc-panelBorder/50 py-2.5">
            <dt className="text-soc-textMuted flex items-center gap-2">
              <Mail size={13} /> Email
            </dt>
            <dd className="text-slate-200 font-mono flex items-center gap-1.5">
              {user?.email}
              {user?.is_email_verified ? (
                <span title="Verified" className="text-soc-success">
                  <BadgeCheck size={14} />
                </span>
              ) : (
                <span className="text-[10px] text-soc-warning uppercase">unverified</span>
              )}
            </dd>
          </div>
          <div className="flex items-center justify-between py-2.5">
            <dt className="text-soc-textMuted flex items-center gap-2">
              <KeyRound size={13} /> Role
            </dt>
            <dd className="text-soc-cyan uppercase font-mono text-xs">{user?.role}</dd>
          </div>
        </dl>
      </Panel>

      <ChangePasswordPanel />

      {user?.role === "admin" ? (
        <AdminSettingsPanel />
      ) : (
        <Panel title="Platform Configuration">
          <div className="flex items-start gap-3">
            <ShieldAlert size={16} className="text-soc-textFaint mt-0.5 shrink-0" />
            <p className="text-sm text-soc-textMuted">
              SMTP, alerting, session timeout, and retention policy are configured by
              administrators. Contact your platform admin to request changes.
            </p>
          </div>
        </Panel>
      )}
    </div>
  );
}

function ChangePasswordPanel() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      setError("Current password is incorrect.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Panel title="Change Password">
      <form onSubmit={handleSubmit} className="space-y-3 max-w-sm">
        <PasswordField label="Current password" value={currentPassword} onChange={setCurrentPassword} />
        <PasswordField label="New password" value={newPassword} onChange={setNewPassword} minLength={8} />
        <PasswordField label="Confirm new password" value={confirmPassword} onChange={setConfirmPassword} minLength={8} />

        {error && (
          <div className="flex items-center gap-2 rounded-lg bg-soc-danger/10 px-3 py-2 text-xs text-soc-danger ring-1 ring-soc-danger/20">
            <AlertCircle size={14} />
            {error}
          </div>
        )}
        {success && (
          <div className="flex items-center gap-2 rounded-lg bg-soc-success/10 px-3 py-2 text-xs text-soc-success ring-1 ring-soc-success/20">
            <CheckCircle2 size={14} />
            Password updated successfully.
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-lg bg-signature-gradient px-4 py-2 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isSubmitting ? "Updating..." : "Update password"}
        </button>
      </form>
    </Panel>
  );
}

function PasswordField({
  label,
  value,
  onChange,
  minLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  minLength?: number;
}) {
  return (
    <div>
      <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">{label}</label>
      <div className="relative">
        <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-soc-textFaint" />
        <input
          type="password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          minLength={minLength}
          required
          className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2 pl-9 pr-3 text-sm text-slate-100 outline-none focus:border-soc-cyan/60 focus:ring-1 focus:ring-soc-cyan/30"
        />
      </div>
    </div>
  );
}
