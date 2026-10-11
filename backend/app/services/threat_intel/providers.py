"""
Threat intelligence provider clients.

Each function is independent: a missing API key, a timeout, or a 4xx/5xx
from one provider never prevents the other two from returning data. Callers
get back (data, error) — `data` is the normalized dict to cache/display,
`error` is a short human-readable reason when `data` is None.

Request/response shapes here match each provider's actual public API docs:
- AbuseIPDB v2 check endpoint
- VirusTotal v3 IP address endpoint
- AlienVault OTX v1 IPv4 general indicator endpoint
"""
import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_TIMEOUT = settings.THREAT_INTEL_REQUEST_TIMEOUT_SECONDS


async def fetch_abuseipdb(client: httpx.AsyncClient, ip: str) -> tuple[dict | None, str | None]:
    if not settings.ABUSEIPDB_API_KEY:
        return None, "not_configured"

    try:
        resp = await client.get(
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": ip, "maxAgeInDays": 90},
            headers={"Key": settings.ABUSEIPDB_API_KEY, "Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json().get("data", {})
        return {
            "abuse_confidence_score": payload.get("abuseConfidenceScore"),
            "total_reports": payload.get("totalReports"),
            "is_whitelisted": payload.get("isWhitelisted"),
            "country_code": payload.get("countryCode"),
            "isp": payload.get("isp"),
            "domain": payload.get("domain"),
            "usage_type": payload.get("usageType"),
        }, None
    except httpx.TimeoutException:
        logger.warning("AbuseIPDB lookup timed out for %s", ip)
        return None, "timeout"
    except httpx.HTTPStatusError as exc:
        logger.warning("AbuseIPDB lookup failed for %s: HTTP %s", ip, exc.response.status_code)
        return None, f"http_{exc.response.status_code}"
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("AbuseIPDB lookup error for %s: %s", ip, exc)
        return None, "request_failed"


async def fetch_virustotal(client: httpx.AsyncClient, ip: str) -> tuple[dict | None, str | None]:
    if not settings.VIRUSTOTAL_API_KEY:
        return None, "not_configured"

    try:
        resp = await client.get(
            f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
            headers={"x-apikey": settings.VIRUSTOTAL_API_KEY},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        attrs = resp.json().get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})
        return {
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "asn": attrs.get("asn"),
            "as_owner": attrs.get("as_owner"),
            "country": attrs.get("country"),
        }, None
    except httpx.TimeoutException:
        logger.warning("VirusTotal lookup timed out for %s", ip)
        return None, "timeout"
    except httpx.HTTPStatusError as exc:
        logger.warning("VirusTotal lookup failed for %s: HTTP %s", ip, exc.response.status_code)
        return None, f"http_{exc.response.status_code}"
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("VirusTotal lookup error for %s: %s", ip, exc)
        return None, "request_failed"


async def fetch_otx(client: httpx.AsyncClient, ip: str) -> tuple[dict | None, str | None]:
    if not settings.OTX_API_KEY:
        return None, "not_configured"

    try:
        resp = await client.get(
            f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/general",
            headers={"X-OTX-API-KEY": settings.OTX_API_KEY},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        pulse_info = payload.get("pulse_info", {})
        return {
            "pulse_count": pulse_info.get("count", 0),
            "country_name": payload.get("country_name"),
            "asn": payload.get("asn"),
            "reputation": payload.get("reputation"),
        }, None
    except httpx.TimeoutException:
        logger.warning("OTX lookup timed out for %s", ip)
        return None, "timeout"
    except httpx.HTTPStatusError as exc:
        logger.warning("OTX lookup failed for %s: HTTP %s", ip, exc.response.status_code)
        return None, f"http_{exc.response.status_code}"
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("OTX lookup error for %s: %s", ip, exc)
        return None, "request_failed"


async def fetch_geolocation(client: httpx.AsyncClient, ip: str) -> tuple[dict | None, str | None]:
    """
    Attacker address lookup, via ip-api.com's free tier — unlike the three
    threat-intel providers above, this needs no API key/signup, so it's
    always attempted rather than gated on settings.*_API_KEY being set.

    Note: ip-api.com's free tier is HTTP-only (no HTTPS) and rate-limited to
    45 requests/minute per source IP — acceptable here since results are
    cached (see ThreatIntelService), so repeat lookups of the same attacker
    IP don't re-hit the API. Private/reserved IPs (RFC 1918, documentation
    ranges like 203.0.113.0/24) correctly fail geolocation — that's expected
    for internal test traffic, not a bug.
    """
    try:
        resp = await client.get(
            f"http://ip-api.com/json/{ip}",
            params={
                "fields": "status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,query"
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()

        if payload.get("status") != "success":
            reason = payload.get("message", "lookup_failed")
            logger.info("Geolocation lookup returned no result for %s: %s", ip, reason)
            return None, reason

        return {
            "city": payload.get("city"),
            "region": payload.get("regionName"),
            "country": payload.get("country"),
            "country_code": payload.get("countryCode"),
            "zip_code": payload.get("zip"),
            "latitude": payload.get("lat"),
            "longitude": payload.get("lon"),
            "timezone": payload.get("timezone"),
            "isp": payload.get("isp"),
            "org": payload.get("org"),
        }, None
    except httpx.TimeoutException:
        logger.warning("Geolocation lookup timed out for %s", ip)
        return None, "timeout"
    except httpx.HTTPStatusError as exc:
        logger.warning("Geolocation lookup failed for %s: HTTP %s", ip, exc.response.status_code)
        return None, f"http_{exc.response.status_code}"
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Geolocation lookup error for %s: %s", ip, exc)
        return None, "request_failed"
