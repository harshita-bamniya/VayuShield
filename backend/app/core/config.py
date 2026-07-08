from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Claude API (used by Module 06 + 07)
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # WhatsApp (Module 07)
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    # Ingestion (Module 03)
    FIRMS_MAP_KEY: str = ""   # NASA FIRMS — get free key at https://firms.modaps.eosdis.nasa.gov/api/


settings = Settings()
