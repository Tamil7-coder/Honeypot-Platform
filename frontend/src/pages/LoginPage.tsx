import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Lock, Mail, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import AuthCard from "../components/AuthCard";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password, rememberMe);
      navigate("/dashboard");
    } catch {
      setError("Invalid email or password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthCard subtitle="Sign in to access the security operations dashboard.">
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

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs text-soc-textMuted font-medium">Password</label>
            <Link to="/forgot-password" className="text-xs text-soc-cyan hover:underline">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-soc-textFaint" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-soc-panelBorder bg-black/30 py-2.5 pl-9 pr-3 text-sm text-slate-100 outline-none transition-colors focus:border-soc-cyan/60 focus:ring-1 focus:ring-soc-cyan/30"
              required
              autoComplete="current-password"
            />
          </div>
        </div>

        <label className="flex items-center gap-2 text-xs text-soc-textMuted cursor-pointer select-none">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-soc-panelBorder bg-black/30 accent-soc-cyan"
          />
          Remember me for 30 days
        </label>

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
          {isSubmitting ? "Authenticating..." : "Sign In"}
        </button>
      </form>
    </AuthCard>
  );
}
