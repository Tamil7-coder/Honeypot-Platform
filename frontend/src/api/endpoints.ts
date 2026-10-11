import { apiClient } from "./client";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface HoneypotStatusItem {
  name: string;
  type: string;
  is_active: boolean;
  session_count: number;
}

export interface AlertItem {
  id: string;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  message: string;
  source_ip: string | null;
  email_sent: boolean;
  created_at: string;
}

export interface DashboardSummary {
  total_attacks: number;
  active_sessions_last_hour: number;
  unique_attacker_ips: number;
  top_targeted_services: { protocol: string; attack_count: number }[];
  top_attacker_ips: { source_ip: string; attack_count: number }[];
  attacks_last_7_days: { day: string; attack_count: number }[];
  active_honeypots: number;
  total_honeypots: number;
  attacks_today: number;
  top_countries: { country_code: string; attack_count: number }[];
  top_usernames: { username: string; attempt_count: number }[];
  top_passwords: { password: string; attempt_count: number }[];
  honeypot_status: HoneypotStatusItem[];
  recent_alerts: AlertItem[];
  avg_risk_score_24h: number | null;
  risk_score_sample_size: number;
}

export interface AttackSession {
  id: string;
  honeypot_id: string;
  session_ref: string;
  source_ip: string;
  protocol: string;
  country_code: string | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  severity: "low" | "medium" | "high" | "critical" | null;
  risk_score: number | null;
}

export interface AttackSessionListResponse {
  total: number;
  items: AttackSession[];
}

export interface CurrentUser {
  id: string;
  username: string;
  full_name: string;
  email: string;
  is_active: boolean;
  is_email_verified: boolean;
  role: "admin" | "analyst" | "viewer";
  created_at: string;
  last_login_at: string | null;
}

export async function login(email: string, password: string, rememberMe = false): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", {
    email,
    password,
    remember_me: rememberMe,
  });
  return data;
}

export async function registerUser(fullName: string, email: string, password: string): Promise<CurrentUser> {
  const { data } = await apiClient.post<CurrentUser>("/auth/register", {
    full_name: fullName,
    email,
    password,
  });
  return data;
}

export async function requestPasswordReset(email: string): Promise<{ detail: string; dev_reset_token?: string }> {
  const { data } = await apiClient.post("/auth/forgot-password", { email });
  return data;
}

export async function resetPassword(token: string, newPassword: string): Promise<CurrentUser> {
  const { data } = await apiClient.post<CurrentUser>("/auth/reset-password", { token, new_password: newPassword });
  return data;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<CurrentUser> {
  const { data } = await apiClient.post<CurrentUser>("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return data;
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const { data } = await apiClient.get<CurrentUser>("/users/me");
  return data;
}

export interface SessionDurationStats {
  avg_seconds: number | null;
  min_seconds: number | null;
  max_seconds: number | null;
  median_seconds: number | null;
}

export interface AdvancedAnalytics {
  hourly_distribution: { hour: number; attack_count: number }[];
  attack_heatmap: { day_of_week: number; hour: number; attack_count: number }[];
  weekly_trend: { week: string; attack_count: number }[];
  monthly_trend: { month: string; attack_count: number }[];
  top_commands: { command: string; execution_count: number }[];
  session_duration: SessionDurationStats;
  risk_distribution: { severity: string; attack_count: number }[];
}

export interface ProviderResult {
  data: Record<string, unknown> | null;
  error: string | null;
}

export interface IpReputation {
  ip_address: string;
  threat_level: "low" | "medium" | "high" | "critical" | null;
  fetched_at: string;
  from_cache: boolean;
  abuseipdb: ProviderResult;
  virustotal: ProviderResult;
  otx: ProviderResult;
  geolocation: ProviderResult;
}

export interface ReplayEvent {
  event_type: "login_success" | "login_failed" | "command" | "download" | "upload" | "disconnect";
  timestamp: string;
  detail: Record<string, unknown>;
}

export interface AttackReplay {
  session: AttackSession;
  timeline: ReplayEvent[];
}

export async function fetchAttackReplay(sessionId: string): Promise<AttackReplay> {
  const { data } = await apiClient.get<AttackReplay>(`/attacks/${sessionId}/replay`);
  return data;
}

export type ReportPeriod = "daily" | "weekly" | "monthly";
export type ReportFormat = "pdf" | "csv" | "xlsx";

export async function downloadReport(period: ReportPeriod, format: ReportFormat): Promise<void> {
  const response = await apiClient.get(`/reports/${period}`, {
    params: { format },
    responseType: "blob",
  });

  const contentDisposition = (response.headers["content-disposition"] as string) ?? "";
  const match = contentDisposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? `honeypot-report-${period}.${format}`;

  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export interface Notification {
  id: string;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  message: string;
  source_ip: string | null;
  email_sent: boolean;
  email_error: string | null;
  is_read: boolean;
  dismissed_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  total: number;
  unread_count: number;
  items: Notification[];
}

export async function fetchNotifications(limit = 30): Promise<NotificationListResponse> {
  const { data } = await apiClient.get<NotificationListResponse>("/notifications", { params: { limit } });
  return data;
}

export async function markNotificationRead(id: string): Promise<Notification> {
  const { data } = await apiClient.patch<Notification>(`/notifications/${id}/read`);
  return data;
}

export async function dismissNotification(id: string): Promise<Notification> {
  const { data } = await apiClient.patch<Notification>(`/notifications/${id}/dismiss`);
  return data;
}

export async function markAllNotificationsRead(): Promise<{ marked_read: number }> {
  const { data } = await apiClient.post<{ marked_read: number }>("/notifications/mark-all-read");
  return data;
}

export interface PlatformSettings {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password_configured: boolean;
  smtp_use_tls: boolean;
  smtp_from_email: string;
  smtp_from_name: string;
  email_enabled: boolean;
  admin_alert_email: string;
  alert_min_severity: string;
  theme: string;
  session_timeout_minutes: number;
  retention_policy_days: number;
  updated_at: string;
}

export type SettingsUpdatePayload = Partial<
  Omit<PlatformSettings, "smtp_password_configured" | "updated_at"> & { smtp_password: string }
>;

export async function fetchSettings(): Promise<PlatformSettings> {
  const { data } = await apiClient.get<PlatformSettings>("/settings");
  return data;
}

export async function updateSettings(payload: SettingsUpdatePayload): Promise<PlatformSettings> {
  const { data } = await apiClient.patch<PlatformSettings>("/settings", payload);
  return data;
}

export async function runRetentionCleanup(): Promise<{ deleted_sessions: number; retention_policy_days: number }> {
  const { data } = await apiClient.post("/settings/run-retention-cleanup");
  return data;
}

export async function sendTestEmail(toEmail: string): Promise<{ success: boolean; detail: string }> {
  const { data } = await apiClient.post("/settings/test-email", { to_email: toEmail });
  return data;
}

export async function fetchIpReputation(ip: string): Promise<IpReputation> {
  const { data } = await apiClient.get<IpReputation>(`/threat-intel/${ip}`);
  return data;
}

export async function fetchAdvancedAnalytics(): Promise<AdvancedAnalytics> {
  const { data } = await apiClient.get<AdvancedAnalytics>("/analytics/advanced");
  return data;
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await apiClient.get<DashboardSummary>("/analytics/dashboard-summary");
  return data;
}

export interface AttackSearchFilters {
  source_ip?: string;
  country_code?: string;
  protocol?: string;
  username?: string;
  password?: string;
  command?: string;
  severity?: string;
  date_from?: string;
  date_to?: string;
  session_ref?: string;
}

export async function fetchAttackSessions(
  skip = 0,
  limit = 50,
  filters: AttackSearchFilters = {}
): Promise<AttackSessionListResponse> {
  const { data } = await apiClient.get<AttackSessionListResponse>("/attacks", {
    params: { skip, limit, ...filters },
  });
  return data;
}
