from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import AppException
from app.db.session import get_db
from app.services.reports.csv_exporter import export_csv
from app.services.reports.data import ReportPeriod, ReportService
from app.services.reports.excel_exporter import export_excel
from app.services.reports.pdf_exporter import export_pdf

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(get_current_user)])

_CONTENT_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}

_EXPORTERS = {
    "csv": export_csv,
    "xlsx": export_excel,
    "pdf": export_pdf,
}


@router.get("/{period}")
def generate_report(period: ReportPeriod, format: str = "pdf", db: Session = Depends(get_db)):
    """
    Generates a Daily/Weekly/Monthly attack report and streams it back as a
    file download in the requested format (pdf, csv, or xlsx). All three
    formats render the exact same underlying ReportData, so they can never
    disagree with each other.
    """
    if format not in _EXPORTERS:
        raise AppException(f"Unsupported format '{format}'. Use one of: pdf, csv, xlsx.", status_code=400)

    service = ReportService(db)
    report = service.build(period)
    file_bytes = _EXPORTERS[format](report)

    filename = f"honeypot-report-{period}-{report.generated_at.strftime('%Y%m%d-%H%M')}.{format}"
    return Response(
        content=file_bytes,
        media_type=_CONTENT_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
