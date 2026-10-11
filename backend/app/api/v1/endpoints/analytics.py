from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.attack import AdvancedAnalyticsResponse, DashboardSummaryResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard-summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    service = AnalyticsService(db)
    return service.get_dashboard_summary()


@router.get("/advanced", response_model=AdvancedAnalyticsResponse)
def get_advanced_analytics(db: Session = Depends(get_db)):
    service = AnalyticsService(db)
    return service.get_advanced_analytics()
