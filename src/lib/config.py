"""Application configuration"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    frontend_url: str = "http://localhost:3000"
    supabase_url: str | None = None
    supabase_key: str | None = None
    supabase_onboarding_table: str = "onboarding"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
