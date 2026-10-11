import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.attack import IpReputation
from app.repositories.ip_reputation_repository import IpReputationRepository
from app.schemas.threat_intel import IpReputationResponse, ProviderResult
from app.services.threat_intel.providers import fetch_abuseipdb, fetch_geolocation, fetch_otx, fetch_virustotal
from app.services.threat_intel.threat_level import compute_threat_level

logger = get_logger(__name__)


class ThreatIntelService:
    def __init__(self, db: Session):
        self.repo = IpReputationRepository(db)

    async def get_or_fetch(self, ip: str) -> IpReputationResponse:
        cached = self.repo.get_by_ip(ip)
        if cached and self._is_fresh(cached):
            return self._to_response(cached, from_cache=True)

        async with httpx.AsyncClient() as client:
            # Concurrent, not sequential: worst case is ~max(timeouts), not
            # the sum of all four — important since each can take several
            # seconds and this endpoint must not tie up the server.
            abuseipdb_result, virustotal_result, otx_result, geo_result = await asyncio.gather(
                fetch_abuseipdb(client, ip),
                fetch_virustotal(client, ip),
                fetch_otx(client, ip),
                fetch_geolocation(client, ip),
            )

        abuseipdb_data, abuseipdb_error = abuseipdb_result
        virustotal_data, virustotal_error = virustotal_result
        otx_data, otx_error = otx_result
        geolocation_data, geolocation_error = geo_result

        threat_level = compute_threat_level(abuseipdb_data, virustotal_data, otx_data)

        record = self.repo.upsert(
            ip,
            abuseipdb_data=abuseipdb_data,
            virustotal_data=virustotal_data,
            otx_data=otx_data,
            geolocation_data=geolocation_data,
            threat_level=threat_level,
        )

        return self._to_response(
            record,
            from_cache=False,
            abuseipdb_error=abuseipdb_error,
            virustotal_error=virustotal_error,
            otx_error=otx_error,
            geolocation_error=geolocation_error,
        )

    def _is_fresh(self, record: IpReputation) -> bool:
        age = datetime.now(timezone.utc) - record.fetched_at
        return age < timedelta(hours=settings.THREAT_INTEL_CACHE_HOURS)

    def _to_response(
        self,
        record: IpReputation,
        *,
        from_cache: bool,
        abuseipdb_error: str | None = None,
        virustotal_error: str | None = None,
        otx_error: str | None = None,
        geolocation_error: str | None = None,
    ) -> IpReputationResponse:
        def resolve_error(data: dict | None, error: str | None, api_key: str | None) -> str | None:
            if data is not None:
                return None
            if error:
                return error
            # Cache hit with no data recorded and no error passed through:
            # infer the most likely reason from current config rather than
            # showing a blank/ambiguous null. api_key=None means "this
            # provider needs no key" (geolocation), so it's just unavailable.
            if api_key is None:
                return "unavailable"
            return "not_configured" if not api_key else "unavailable"

        return IpReputationResponse(
            ip_address=str(record.ip_address),
            threat_level=record.threat_level.value if record.threat_level else None,
            fetched_at=record.fetched_at,
            from_cache=from_cache,
            abuseipdb=ProviderResult(
                data=record.abuseipdb_data,
                error=resolve_error(record.abuseipdb_data, abuseipdb_error, settings.ABUSEIPDB_API_KEY),
            ),
            virustotal=ProviderResult(
                data=record.virustotal_data,
                error=resolve_error(record.virustotal_data, virustotal_error, settings.VIRUSTOTAL_API_KEY),
            ),
            otx=ProviderResult(
                data=record.otx_data, error=resolve_error(record.otx_data, otx_error, settings.OTX_API_KEY)
            ),
            geolocation=ProviderResult(
                data=record.geolocation_data,
                error=resolve_error(record.geolocation_data, geolocation_error, None),
            ),
        )
