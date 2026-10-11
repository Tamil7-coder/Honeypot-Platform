from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attack import IpReputation, Severity


class IpReputationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_ip(self, ip: str) -> IpReputation | None:
        stmt = select(IpReputation).where(IpReputation.ip_address == ip)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(
        self,
        ip: str,
        *,
        abuseipdb_data: dict | None,
        virustotal_data: dict | None,
        otx_data: dict | None,
        geolocation_data: dict | None = None,
        threat_level: Severity | None,
    ) -> IpReputation:
        existing = self.get_by_ip(ip)
        if existing:
            existing.abuseipdb_data = abuseipdb_data
            existing.virustotal_data = virustotal_data
            existing.otx_data = otx_data
            existing.geolocation_data = geolocation_data
            existing.threat_level = threat_level
            self.db.commit()
            self.db.refresh(existing)
            return existing

        record = IpReputation(
            ip_address=ip,
            abuseipdb_data=abuseipdb_data,
            virustotal_data=virustotal_data,
            otx_data=otx_data,
            geolocation_data=geolocation_data,
            threat_level=threat_level,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
