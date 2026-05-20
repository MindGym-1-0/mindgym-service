from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    _api_env_path = Path(__file__).resolve().parents[1] / 'api' / '.env'
    _repo_env_path = Path(__file__).resolve().parents[2] / '.env'

    model_config = SettingsConfigDict(
        env_file=(_api_env_path, _repo_env_path),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    supabase_url: str = Field(alias='SUPABASE_URL')
    supabase_anon_key: str = Field(alias='SUPABASE_ANON_KEY')
    supabase_service_role_key: str | None = Field(default=None, alias='SUPABASE_SERVICE_ROLE_KEY')
    supabase_jwt_secret: str | None = Field(default=None, alias='SUPABASE_JWT_SECRET')
    legacy_jwt_secret: str | None = Field(default=None, alias='JWT_SECRET')
    app_env: str = Field(default='development', alias='APP_ENV')
    auth_cookie_secure: bool | None = Field(default=None, alias='AUTH_COOKIE_SECURE')
    auth_cookie_samesite: str = Field(default='lax', alias='AUTH_COOKIE_SAMESITE')
    auth_cookie_domain: str | None = Field(default=None, alias='AUTH_COOKIE_DOMAIN')

    @property
    def resolved_supabase_jwt_secret(self) -> str | None:
        return self.supabase_jwt_secret or self.legacy_jwt_secret

    @property
    def resolved_auth_cookie_secure(self) -> bool:
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure

        return self.app_env.lower() not in {'local', 'development', 'dev'}

    @property
    def resolved_auth_cookie_samesite(self) -> str:
        value = self.auth_cookie_samesite.lower()
        if value not in {'lax', 'strict', 'none'}:
            return 'lax'
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
