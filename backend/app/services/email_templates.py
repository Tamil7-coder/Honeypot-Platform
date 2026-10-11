"""
Email templates for attack alerts. Kept separate from AlertService so the
content/formatting can evolve (or be swapped for a templating engine like
Jinja2) without touching the orchestration logic that decides *when* to
send.
"""
from app.core.config import settings
from app.models.attack import AttackSession, Severity

_SEVERITY_COLORS = {
    Severity.LOW: "#34d399",
    Severity.MEDIUM: "#f59e0b",
    Severity.HIGH: "#fb923c",
    Severity.CRITICAL: "#f43f5e",
}

_RECOMMENDATIONS = {
    Severity.CRITICAL: (
        "This session shows signs of post-exploitation activity (payload download, "
        "privilege escalation, or a reverse shell attempt). Recommended: block this "
        "source IP at the firewall/edge immediately and review other sessions from "
        "the same IP or subnet for related activity."
    ),
    Severity.HIGH: (
        "This session combined a successful or high-volume login with command "
        "execution. Recommended: review the commands executed below and consider "
        "blocking this source IP if the pattern repeats."
    ),
}


def build_attack_alert_email(
    *,
    session: AttackSession,
    login_attempts: list[dict],
    command_texts: list[str],
) -> tuple[str, str, str]:
    """Returns (subject, html_body, text_body) for a session alert email."""

    severity = session.severity or Severity.LOW
    color = _SEVERITY_COLORS.get(severity, "#8b96a8")
    recommendation = _RECOMMENDATIONS.get(
        severity, "Review this session in the Attack Monitor for further context."
    )

    session_link = f"{settings.FRONTEND_BASE_URL}/attacks?ip={session.source_ip}"
    dashboard_link = f"{settings.FRONTEND_BASE_URL}/dashboard"

    credential_lines = (
        "\n".join(
            f"  - {a['username']} / {a['password']} ({'SUCCESS' if a['success'] else 'failed'})"
            for a in login_attempts
        )
        or "  (none captured)"
    )
    commands_block = "\n".join(f"  $ {c}" for c in command_texts) or "  (none captured)"

    subject = f"[{severity.value.upper()}] Honeynet SOC Alert — {session.protocol.upper()} attack from {session.source_ip}"

    text_body = f"""HONEYNET SOC — SECURITY ALERT ({severity.value.upper()})

Attack Time:      {session.started_at.isoformat()}
Source IP:        {session.source_ip}
Country:          {session.country_code or 'Unknown'}
Target Service:   {session.protocol.upper()}

Credentials attempted:
{credential_lines}

Commands executed:
{commands_block}

Security Recommendation:
{recommendation}

View this session:  {session_link}
Open dashboard:      {dashboard_link}

-- Honeynet SOC Attack Analytics Platform
"""

    credential_rows_html = "".join(
        f"<tr><td style='padding:4px 8px;font-family:monospace'>{a['username']}</td>"
        f"<td style='padding:4px 8px;font-family:monospace'>{a['password']}</td>"
        f"<td style='padding:4px 8px'>{'success' if a['success'] else 'failed'}</td></tr>"
        for a in login_attempts
    ) or "<tr><td colspan='3' style='padding:8px;color:#8b96a8'>No credentials captured</td></tr>"

    commands_html = (
        "".join(
            f"<div style='font-family:monospace;font-size:12px;padding:2px 0'>$ {c}</div>"
            for c in command_texts
        )
        or "<p style='color:#8b96a8;font-size:13px'>No commands captured</p>"
    )

    html_body = f"""
    <div style="font-family:Arial,sans-serif;background:#080b12;color:#e2e8f0;padding:24px;max-width:600px;margin:auto">
      <div style="border-left:4px solid {color};padding:12px 16px;background:#10141d;border-radius:6px;margin-bottom:20px">
        <span style="color:{color};font-weight:bold;letter-spacing:1px">{severity.value.upper()} SEVERITY</span>
        <h2 style="margin:6px 0 0 0;color:#f1f5f9">Attack Detected: {session.protocol.upper()} from {session.source_ip}</h2>
      </div>

      <table style="width:100%;border-collapse:collapse;margin-bottom:20px;font-size:13px">
        <tr><td style="color:#8b96a8;padding:4px 8px">Attack Time</td><td style="padding:4px 8px">{session.started_at.isoformat()}</td></tr>
        <tr><td style="color:#8b96a8;padding:4px 8px">Source IP</td><td style="padding:4px 8px;font-family:monospace">{session.source_ip}</td></tr>
        <tr><td style="color:#8b96a8;padding:4px 8px">Country</td><td style="padding:4px 8px">{session.country_code or 'Unknown'}</td></tr>
        <tr><td style="color:#8b96a8;padding:4px 8px">Target Service</td><td style="padding:4px 8px">{session.protocol.upper()}</td></tr>
      </table>

      <h3 style="color:#f1f5f9;font-size:14px;margin-bottom:6px">Credentials Attempted</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:20px;font-size:13px;background:#10141d;border-radius:6px">
        {credential_rows_html}
      </table>

      <h3 style="color:#f1f5f9;font-size:14px;margin-bottom:6px">Commands Executed</h3>
      <div style="background:#10141d;border-radius:6px;padding:10px;margin-bottom:20px">
        {commands_html}
      </div>

      <h3 style="color:#f1f5f9;font-size:14px;margin-bottom:6px">Security Recommendation</h3>
      <p style="font-size:13px;color:#cbd5e1;margin-bottom:20px">{recommendation}</p>

      <a href="{session_link}" style="display:inline-block;background:linear-gradient(135deg,#22d3ee,#6366f1);color:#000;text-decoration:none;padding:10px 16px;border-radius:6px;font-weight:600;font-size:13px;margin-right:8px">View Session</a>
      <a href="{dashboard_link}" style="display:inline-block;background:#1e293b;color:#e2e8f0;text-decoration:none;padding:10px 16px;border-radius:6px;font-weight:600;font-size:13px">Open Dashboard</a>

      <p style="color:#5b6579;font-size:11px;margin-top:24px">Honeynet SOC Attack Analytics Platform</p>
    </div>
    """

    return subject, html_body, text_body
