import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Mail, ArrowLeft, CheckCircle2 } from "lucide-react";
import { requestPasswordReset } from "../api/endpoints";
import AuthCard from "../components/AuthCard";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const result = await requestPasswordReset(email);
      setSubmitted(true);
      setDevToken(result.dev_reset_token ?? null);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <AuthCard subtitle="Check your inbox for a reset link.">
        <div className="flex flex-col items-center gap-3 text-center py-2">
          <CheckCircle2 size={28} className="text-soc-success" />
          <p className="text-sm text-slate-200">
            If <span className="font-mono text-soc-cyan">{email}</span> is registered, a password reset
            link has been sent.
          </p>
          {devToken && (
            <div className="w-full rounded-lg bg-soc-warning/10 ring-1 ring-soc-warning/20 p-3 text-left">
              <p className="text-xs text-soc-warning font-medium mb-1">Development mode</p>
              <p className="text-xs text-soc-textMuted mb-2">
                Real email delivery arrives in Phase 3 (SMTP). For now, use this link directly:
              </p>
              <Link
                to={`/reset-password?token=${devToken}`}
                className="text-xs text-soc-cyan hover:underline break-all"
              >
                Continue to reset password →
              </Link>
            </div>
          )}
          <Link to="/login" className="mt-2 flex items-center gap-1.5 text-xs text-soc-textMuted hover:text-slate-100">
            <ArrowLeft size={12} /> Back to sign in
          </Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard subtitle="Enter your email and we'll send you a reset link.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs text-soc-textMuted mb-1.5 font-medium">Email</label>
          <div className="relative">
            <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-soc-textFaint" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2.5 pl-9 pr-3 text-sm text-slate-100 outline-none transition-colors focus:border-soc-cyan/60 focus:ring-1 focus:ring-soc-cyan/30"
              required
              autoFocus
              autoComplete="email"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-lg bg-signature-gradient py-2.5 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isSubmitting ? "Sending..." : "Send reset link"}
        </button>

        <Link to="/login" className="flex items-center justify-center gap-1.5 text-xs text-soc-textMuted hover:text-slate-100">
          <ArrowLeft size={12} /> Back to sign in
        </Link>
      </form>
    </AuthCard>
  );
}
