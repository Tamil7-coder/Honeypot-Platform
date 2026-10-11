import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Lock, AlertCircle, CheckCircle2 } from "lucide-react";
import { resetPassword } from "../api/endpoints";
import AuthCard from "../components/AuthCard";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      await resetPassword(token, newPassword);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch {
      setError("This reset link is invalid or has expired. Request a new one.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!token) {
    return (
      <AuthCard subtitle="Missing reset token.">
        <div className="text-center space-y-3">
          <p className="text-sm text-soc-textMuted">
            This link is missing its reset token. Request a new password reset email.
          </p>
          <Link to="/forgot-password" className="text-sm text-soc-cyan hover:underline">
            Request a new link
          </Link>
        </div>
      </AuthCard>
    );
  }

  if (success) {
    return (
      <AuthCard subtitle="Password updated.">
        <div className="flex flex-col items-center gap-3 text-center py-2">
          <CheckCircle2 size={28} className="text-soc-success" />
          <p className="text-sm text-slate-200">Your password has been reset. Redirecting to sign in...</p>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard subtitle="Choose a new password for your account.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">New password</label>
          <div className="relative">
            <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-soc-textFaint" />
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2.5 pl-9 pr-3 text-sm text-slate-100 outline-none transition-colors focus:border-soc-cyan/60 focus:ring-1 focus:ring-soc-cyan/30"
              required
              autoFocus
              minLength={8}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">Confirm new password</label>
          <div className="relative">
            <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-soc-textFaint" />
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2.5 pl-9 pr-3 text-sm text-slate-100 outline-none transition-colors focus:border-soc-cyan/60 focus:ring-1 focus:ring-soc-cyan/30"
              required
              minLength={8}
            />
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg bg-soc-danger/10 px-3 py-2 text-xs text-soc-danger ring-1 ring-soc-danger/20">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-lg bg-signature-gradient py-2.5 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isSubmitting ? "Resetting..." : "Reset password"}
        </button>
      </form>
    </AuthCard>
  );
}
