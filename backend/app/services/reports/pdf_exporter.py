import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.reports.data import ReportData

_ACCENT = colors.HexColor("#0e7490")
_HEADER_BG = colors.HexColor("#0f172a")
_HEADER_TEXT = colors.white
_ROW_ALT = colors.HexColor("#f1f5f9")


def _table_style(header_rows: int = 1) -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, header_rows - 1), _HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), _HEADER_TEXT),
            ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, _ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def export_pdf(report: ReportData) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=16 * mm, rightMargin=16 * mm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], textColor=_ACCENT, fontSize=18)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], textColor=colors.grey, fontSize=9)

    elements = [
        Paragraph("Honeynet SOC — Attack Report", title_style),
        Paragraph(report.period_label, styles["Normal"]),
        Paragraph(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}", meta_style),
        Spacer(1, 10 * mm),
    ]

    elements.append(Paragraph("Summary", section_style))
    elements.append(
        Table(
            [["Total Attacks", str(report.total_attacks)], ["Unique Attacker IPs", str(report.unique_attacker_ips)]],
            colWidths=[80 * mm, 80 * mm],
            style=_table_style(header_rows=0),
        )
    )

    elements.append(Paragraph("Severity Breakdown", section_style))
    sev_rows = [["Severity", "Count"]] + [
        [r["severity"].upper(), str(r["attack_count"])] for r in report.severity_breakdown
    ] or [["No data", ""]]
    elements.append(Table(sev_rows, colWidths=[80 * mm, 80 * mm], style=_table_style()))

    elements.append(Paragraph("Top Attacker IPs", section_style))
    ip_rows = [["Source IP", "Attack Count"]] + [
        [r["source_ip"], str(r["attack_count"])] for r in report.top_attacker_ips
    ]
    if len(ip_rows) == 1:
        ip_rows.append(["No data in this period", ""])
    elements.append(Table(ip_rows, colWidths=[100 * mm, 60 * mm], style=_table_style()))

    elements.append(Paragraph("Top Countries", section_style))
    country_rows = [["Country", "Attack Count"]] + [
        [r["country_code"], str(r["attack_count"])] for r in report.top_countries
    ]
    if len(country_rows) == 1:
        country_rows.append(["No data in this period", ""])
    elements.append(Table(country_rows, colWidths=[100 * mm, 60 * mm], style=_table_style()))

    elements.append(Paragraph("Top Credentials Attempted", section_style))
    cred_rows = [["Username", "Password", "Attempts"]] + [
        [r["username"], r["password"], str(r["attempt_count"])] for r in report.top_credentials
    ]
    if len(cred_rows) == 1:
        cred_rows.append(["No data in this period", "", ""])
    elements.append(Table(cred_rows, colWidths=[60 * mm, 60 * mm, 40 * mm], style=_table_style()))

    elements.append(Paragraph(f"Sessions (top {min(len(report.sessions), 25)} by risk score)", section_style))
    session_rows = [["Source IP", "Protocol", "Severity", "Risk", "Started"]] + [
        [
            s.source_ip,
            s.protocol.upper(),
            (s.severity.value if s.severity else "—").upper(),
            str(s.risk_score) if s.risk_score is not None else "—",
            s.started_at.strftime("%Y-%m-%d %H:%M"),
        ]
        for s in report.sessions[:25]
    ]
    if len(session_rows) == 1:
        session_rows.append(["No sessions in this period", "", "", "", ""])
    elements.append(Table(session_rows, colWidths=[38 * mm, 22 * mm, 22 * mm, 18 * mm, 40 * mm], style=_table_style()))

    doc.build(elements)
    return buf.getvalue()
