from app.models.attack import Severity


def compute_threat_level(
    abuseipdb_data: dict | None, virustotal_data: dict | None, otx_data: dict | None
) -> Severity | None:
    """Combine whichever providers succeeded into a single LOW..CRITICAL
    threat level. Returns None if every configured provider failed or none
    are configured — the caller/UI shows "insufficient data" rather than a
    fabricated default."""

    if abuseipdb_data is None and virustotal_data is None and otx_data is None:
        return None

    abuse_score = (abuseipdb_data or {}).get("abuse_confidence_score") or 0
    vt_malicious = (virustotal_data or {}).get("malicious") or 0
    otx_pulses = (otx_data or {}).get("pulse_count") or 0

    if abuse_score >= 75 or vt_malicious >= 5 or otx_pulses >= 10:
        return Severity.CRITICAL
    if abuse_score >= 40 or vt_malicious >= 1 or otx_pulses >= 3:
        return Severity.HIGH
    if abuse_score >= 10 or otx_pulses >= 1:
        return Severity.MEDIUM
    return Severity.LOW
