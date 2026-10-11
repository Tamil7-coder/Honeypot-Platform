import csv
import io

from app.services.reports.data import ReportData


def export_csv(report: ReportData) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow([report.period_label])
    writer.writerow([f"Generated: {report.generated_at.isoformat()}"])
    writer.writerow([])
    writer.writerow(["Total Attacks", report.total_attacks])
    writer.writerow(["Unique Attacker IPs", report.unique_attacker_ips])
    writer.writerow([])

    writer.writerow(["-- Severity Breakdown --"])
    writer.writerow(["Severity", "Count"])
    for row in report.severity_breakdown:
        writer.writerow([row["severity"], row["attack_count"]])
    writer.writerow([])

    writer.writerow(["-- Top Attacker IPs --"])
    writer.writerow(["Source IP", "Attack Count"])
    for row in report.top_attacker_ips:
        writer.writerow([row["source_ip"], row["attack_count"]])
    writer.writerow([])

    writer.writerow(["-- Top Countries --"])
    writer.writerow(["Country Code", "Attack Count"])
    for row in report.top_countries:
        writer.writerow([row["country_code"], row["attack_count"]])
    writer.writerow([])

    writer.writerow(["-- Top Credentials Attempted --"])
    writer.writerow(["Username", "Password", "Attempt Count"])
    for row in report.top_credentials:
        writer.writerow([row["username"], row["password"], row["attempt_count"]])
    writer.writerow([])

    writer.writerow(["-- Sessions --"])
    writer.writerow(["Source IP", "Protocol", "Country", "Severity", "Risk Score", "Started At", "Duration (s)"])
    for s in report.sessions:
        writer.writerow(
            [
                s.source_ip,
                s.protocol,
                s.country_code or "",
                s.severity.value if s.severity else "unclassified",
                s.risk_score if s.risk_score is not None else "",
                s.started_at.isoformat(),
                s.duration_seconds if s.duration_seconds is not None else "",
            ]
        )

    return buf.getvalue().encode("utf-8")
