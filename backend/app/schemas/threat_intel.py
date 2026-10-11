from datetime import datetime

from pydantic import BaseModel


class ProviderResult(BaseModel):
    data: dict | None
    error: str | None  # e.g. "not_configured", "timeout", "http_429", None if data present


class IpReputationResponse(BaseModel):
    ip_address: str
    threat_level: str | None  # low | medium | high | critical | None (insufficient data)
    fetched_at: datetime
    from_cache: bool
    abuseipdb: ProviderResult
    virustotal: ProviderResult
    otx: ProviderResult
    geolocation: ProviderResult
