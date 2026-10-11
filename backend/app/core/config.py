"""
Centralized application configuration.

All environment-dependent values are loaded here so that no other module
reads os.environ directly. This keeps configuration a single source of truth
(SOLID - Single Responsibility) and makes testing/overriding trivial.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- General ---
    PROJECT_NAME: str = "Honeypots with Attack Analytics"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # --- Security ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    REMEMBER_ME_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # --- Database ---
    POSTGRES_USER: str = "honeypot_admin"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "honeypot_platform"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost"]

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # --- Email alerts (Phase 3) ---
    # Works with any standard SMTP provider: Gmail (use an App Password, not
    # your account password), Mailtrap (sandbox, for development), or any
    # corporate SMTP relay. Leave EMAIL_ENABLED=false to run without SMTP
    # configured — ingestion and everything else keeps working normally.
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "alerts@honeypot-platform.local"
    SMTP_FROM_NAME: str = "Honeynet SOC"

    ADMIN_ALERT_EMAIL: str = ""
    ALERT_MIN_SEVERITY: str = "high"  # sessions at or above this severity trigger an email
    FRONTEND_BASE_URL: str = "http://localhost"

    # --- Threat Intelligence (Phase 6) ---
    # Each provider is independent and optional: leave any key blank to skip
    # that provider gracefully (its section of the response is simply marked
    # "not configured" rather than the whole lookup failing).
    ABUSEIPDB_API_KEY: str = ""
    VIRUSTOTAL_API_KEY: str = ""
    OTX_API_KEY: str = ""
    THREAT_INTEL_CACHE_HOURS: int = 24
    THREAT_INTEL_REQUEST_TIMEOUT_SECONDS: float = 8.0

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
