from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_KEY = "change_me_in_production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "VayuShield AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vayushield:vayushield_dev@localhost:5432/vayushield"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Seed admin (Module 00 only — remove after Module 01 onboarding wizard lands)
    SEED_ADMIN_EMAIL: str = "admin@vayushield.local"
    SEED_ADMIN_PASSWORD: str = "Admin@123"

    # Groq API (used by Module 06 + 07 for AI evidence briefs and advisories)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    @model_validator(mode="after")
    def _check_secret_key(self) -> "Settings":
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == _INSECURE_KEY:
            raise ValueError(
                "SECRET_KEY must be changed from the default before running in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self

    # WhatsApp — Meta Cloud API (future)
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    # WhatsApp — Twilio API (active integration)
    TWILIO_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "+14155238886"  # Twilio sandbox number

    # Ingestion (Module 03)
    FIRMS_MAP_KEY: str = ""       # NASA FIRMS — https://firms.modaps.eosdis.nasa.gov/api/
    CPCB_API_KEY: str = ""        # data.gov.in CPCB real-time AQ — https://api.data.gov.in/
    WAQI_TOKEN: str = ""          # aqicn.org WAQI — https://aqicn.org/data-platform/token/
    EARTHDATA_TOKEN: str = ""     # NASA Earthdata — https://earthdata.nasa.gov/
    TOMTOM_API_KEY: str = ""      # TomTom Traffic — https://developer.tomtom.com/


settings = Settings()
