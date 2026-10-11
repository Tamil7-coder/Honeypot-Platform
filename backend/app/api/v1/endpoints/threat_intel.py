from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.threat_intel import IpReputationResponse
from app.services.threat_intel_service import ThreatIntelService

router = APIRouter(prefix="/threat-intel", tags=["Threat Intelligence"], dependencies=[Depends(get_current_user)])


@router.get("/{ip}", response_model=IpReputationResponse)
async def get_ip_reputation(ip: str, db: Session = Depends(get_db)):
    """
    Looks up threat intelligence for an attacker IP, aggregating AbuseIPDB,
    VirusTotal, and AlienVault OTX. Results are cached for
    THREAT_INTEL_CACHE_HOURS; any provider without an API key configured
    (or that errors/times out) is reported per-field rather than failing
    the whole lookup.
    """
    service = ThreatIntelService(db)
    return await service.get_or_fetch(ip)
