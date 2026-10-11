"""
Risk Scoring Engine (Phase 7).

Computes a weighted 0-100 risk score from raw session signals and maps it
to a Severity band. This replaces the interim pattern-matching heuristic
built in Phase 3 -- by design, only the internals changed; AttackService's
call site needed only a one-field addition (persisting the numeric score
alongside the severity it already stored), and every downstream consumer
(AlertService, WebSocket broadcasts, SeverityBadge, the dashboard) needed
zero changes.

Scoring factors, per the project brief:
- Failed logins            (brute-force volume)
- Distinct passwords tried (credential-stuffing breadth)
- SSH login success        (real interactive shell obtained -- high value)
- wget / curl              (payload staging)
- chmod +x                 (making a downloaded payload executable)
- Download + chmod combo   (classic stage-and-execute pattern)
- Reverse shell signatures (nc -e, /dev/tcp, bash -i, python socket)
- Privilege escalation     (sudo/su -, reading /etc/shadow)
"""
import re
from dataclasses import dataclass

from app.models.attack import Severity

_REVERSE_SHELL_PATTERNS = [
    r"\bnc\s+-e\b",
    r"/dev/tcp/",
    r"\bbash\s+-i\b",
    r"\bpython[0-9.]*\s+-c\b.*socket",
    r"\bperl\s+-e\b.*socket",
]

_PRIVESC_PATTERNS = [
    r"\b(sudo|su)\s+-",
    r"\bcat\s+/etc/shadow\b",
    r"\bchmod\s+u\+s\b",
]

# Multi-honeypot exploit signals: not tied to any one protocol's syntax, so
# these apply regardless of which honeypot/protocol produced the command
# text -- e.g. Dionaea's SMB handler logging "SMB exploit shellcode
# detected" when it catches an EternalBlue-style attack.
_EXPLOIT_PATTERNS = [
    r"\bshellcode\b",
    r"\bexploit\b",
    r"\bbuffer\s*overflow\b",
    r"\bmetasploit\b",
]

_DOWNLOAD_PATTERNS = [r"\bwget\b", r"\bcurl\b"]
_CHMOD_X_PATTERN = r"\bchmod\s+\+x\b"


@dataclass(frozen=True)
class RiskAssessment:
    score: int  # 0-100
    severity: Severity
    factors: list[str]  # human-readable list of which signals fired, for transparency/debugging


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def compute_risk_score(
    *,
    protocol: str,
    login_success: bool,
    failed_login_count: int,
    distinct_password_count: int,
    command_texts: list[str],
    file_count: int = 0,
) -> RiskAssessment:
    score = 0
    factors: list[str] = []
    combined_commands = " ".join(command_texts)

    # --- Login behavior ---
    failed_login_points = min(failed_login_count * 2, 20)
    if failed_login_points:
        score += failed_login_points
        factors.append(f"{failed_login_count} failed login attempt(s) (+{failed_login_points})")

    if distinct_password_count >= 10:
        score += 10
        factors.append(f"{distinct_password_count} distinct passwords tried -- brute-force pattern (+10)")

    if login_success:
        if protocol.lower() == "ssh":
            score += 15
            factors.append("Successful SSH login -- real interactive shell obtained (+15)")
        else:
            score += 8
            factors.append(f"Successful {protocol.upper()} login (+8)")

    # --- File transfers (any protocol: SSH/HTTP/FTP payload staging) ---
    if file_count > 0:
        score += 15
        factors.append(f"{file_count} file transfer(s) detected -- possible payload staging (+15)")

    # --- Post-exploitation commands ---
    has_download = bool(combined_commands) and _matches_any(_DOWNLOAD_PATTERNS, combined_commands)
    has_chmod_x = bool(combined_commands) and bool(re.search(_CHMOD_X_PATTERN, combined_commands, re.IGNORECASE))

    if has_download:
        score += 10
        factors.append("Payload download command (wget/curl) (+10)")

    if has_chmod_x:
        score += 15
        factors.append("chmod +x on a file -- preparing to execute a payload (+15)")

    if has_download and has_chmod_x:
        score += 15
        factors.append("Download-then-execute staging pattern (+15)")

    if combined_commands and _matches_any(_REVERSE_SHELL_PATTERNS, combined_commands):
        score += 40
        factors.append("Reverse shell signature detected (+40)")

    if combined_commands and _matches_any(_PRIVESC_PATTERNS, combined_commands):
        score += 25
        factors.append("Privilege escalation attempt (+25)")

    # --- Multi-honeypot exploit signals (protocol-independent) ---
    if combined_commands and _matches_any(_EXPLOIT_PATTERNS, combined_commands):
        score += 50
        factors.append("Exploit/shellcode signature detected -- real attack payload captured (+50)")

    score = min(score, 100)
    severity = _score_to_severity(score)
    return RiskAssessment(score=score, severity=severity, factors=factors)


def _score_to_severity(score: int) -> Severity:
    if score >= 70:
        return Severity.CRITICAL
    if score >= 40:
        return Severity.HIGH
    if score >= 10:
        return Severity.MEDIUM
    return Severity.LOW


_SEVERITY_ORDER = {Severity.LOW: 0, Severity.MEDIUM: 1, Severity.HIGH: 2, Severity.CRITICAL: 3}


def meets_threshold(severity: Severity, threshold: Severity) -> bool:
    """True if `severity` is at or above `threshold` in the LOW..CRITICAL ordering."""
    return _SEVERITY_ORDER[severity] >= _SEVERITY_ORDER[threshold]
