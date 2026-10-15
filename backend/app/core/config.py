from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory, so `.env` is found no matter where commands are run from.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Kamareddy Wedding Marketplace API"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None

    # Comma-separated origins, e.g. "http://localhost:5173,http://127.0.0.1:5173"
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Authentication ---
    SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Set COOKIE_SECURE=true whenever the site is served over HTTPS.
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict"] = "lax"

    # --- Rate limiting (in-memory, per client IP) ---
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT: int = 10
    LOGIN_RATE_WINDOW_SECONDS: int = 300
    REGISTER_RATE_LIMIT: int = 10
    REGISTER_RATE_WINDOW_SECONDS: int = 3600

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
