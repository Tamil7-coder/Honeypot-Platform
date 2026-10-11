from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings import PlatformSettings


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self) -> PlatformSettings:
        """Returns the single settings row, creating it with defaults if
        somehow missing (e.g. a database restored without running the
        Phase 12 migration's seed step)."""
        row = self.db.execute(select(PlatformSettings).limit(1)).scalar_one_or_none()
        if row is None:
            row = PlatformSettings()
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
        return row

    def save(self, settings: PlatformSettings) -> PlatformSettings:
        self.db.commit()
        self.db.refresh(settings)
        return settings
