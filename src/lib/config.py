"""Application configuration"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file for legacy OS getters fallback stability
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    _api_env_path = Path(__file__).resolve().parents[1] / "api" / ".env"
    _repo_env_path = Path(__file__).resolve().parents[2] / ".env"

    model_config = SettingsConfigDict(
        env_file=(_api_env_path, _repo_env_path),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    frontend_url: str = "http://localhost:3000"
    supabase_onboarding_table: str = "onboarding"

    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "SUPABASE_KEY"),
    )
    supabase_service_role_key: str | None = Field(
        default=None, alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    supabase_jwt_secret: str | None = Field(default=None, alias="SUPABASE_JWT_SECRET")
    legacy_jwt_secret: str | None = Field(default=None, alias="JWT_SECRET")
    app_env: str = Field(default="development", alias="APP_ENV")
    auth_cookie_secure: bool | None = Field(default=None, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", alias="AUTH_COOKIE_SAMESITE")
    auth_cookie_domain: str | None = Field(default=None, alias="AUTH_COOKIE_DOMAIN")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    @property
    def resolved_supabase_jwt_secret(self) -> str | None:
        return self.supabase_jwt_secret or self.legacy_jwt_secret

    @property
    def supabase_key(self) -> str | None:
        return self.supabase_anon_key

    @property
    def resolved_auth_cookie_secure(self) -> bool:
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure

        return self.app_env.lower() not in {"local", "development", "dev"}

    @property
    def resolved_auth_cookie_samesite(self) -> str:
        value = self.auth_cookie_samesite.lower()
        if value not in {"lax", "strict", "none"}:
            return "lax"
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


class _LazySettings:
    def __getattr__(self, item: str):
        return getattr(get_settings(), item)


settings = _LazySettings()


# --- Legacy Function Wrappers for Feature Modules ---


def supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip()


def supabase_anon_key() -> str:
    return os.getenv("SUPABASE_ANON_KEY", "").strip()


def supabase_service_role_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


def cors_origins_raw() -> str:
    return os.getenv("CORS_ORIGINS", "").strip()


def auth_api_key() -> str:
    """Value for `apikey` when calling Supabase Auth `/auth/v1/user`."""
    return supabase_anon_key() or supabase_service_role_key()


def cors_origin_list() -> list[str]:
    raw = cors_origins_raw()
    if not raw or raw.strip() == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]
