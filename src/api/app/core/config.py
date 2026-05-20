from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    _api_env_path = Path(__file__).resolve().parents[2] / '.env'
    _repo_env_path = Path(__file__).resolve().parents[4] / '.env'

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

    @property
    def resolved_supabase_jwt_secret(self) -> str | None:
        return self.supabase_jwt_secret or self.legacy_jwt_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
