from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings

# Repo root `.env` is the single source of truth shared with admin-web and mobile.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "MedaZone API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "changeme-super-secret-key-at-least-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24   # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Database ──────────────────────────────────────────────────────────────
    # Full async DSN: postgresql+asyncpg://user:pass@host:port/db
    DATABASE_URL: str = (
        "postgresql+asyncpg://medazone:medazone_dev@localhost:5432/medazone"
    )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """psycopg2-compatible URL for Alembic (synchronous migrations)."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

    # ── Redis ─────────────────────────────────────────────────────────────────
    # Full Redis DSN: redis://:password@host:port/db  or  redis://host:port/db
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Firebase / FCM ────────────────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    # ── Chapa payment gateway ─────────────────────────────────────────────────
    CHAPA_SECRET: str = ""
    CHAPA_WEBHOOK_SECRET: str = ""
    CHAPA_WEBHOOK_URL: str = ""  # Override for webhook callback; defaults to API_BASE_URL + path

    @property
    def CHAPA_ENABLED(self) -> bool:
        return bool(self.CHAPA_SECRET.strip())

    # ── ArifPay payment gateway ───────────────────────────────────────────────
    ARIFPAY_SECRET: str = ""
    ARIFPAY_SANDBOX: bool = True
    ARIFPAY_BASE_URL: str = "https://gateway.arifpay.net"

    @property
    def ARIFPAY_ENABLED(self) -> bool:
        return bool(self.ARIFPAY_SECRET.strip())

    # ── Public API base URL (used to build webhook callback URLs) ─────────────
    API_BASE_URL: str = "http://localhost:8001"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated origins in the .env, e.g.:
    #   BACKEND_CORS_ORIGINS=http://localhost:5173,https://admin.medazone.et
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    # ── Geolocation defaults ──────────────────────────────────────────────────
    DEFAULT_SEARCH_RADIUS_KM: float = 10.0
    MAX_SEARCH_RADIUS_KM: float = 50.0

    class Config:
        env_file = (
            str(_REPO_ROOT / ".env"),
            str(_REPO_ROOT / "backend" / ".env"),
            ".env",
        )
        case_sensitive = True
        extra = "ignore"  # silently discard unknown env vars (e.g. DEV_HOST, ARIFPAY_BANK)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
