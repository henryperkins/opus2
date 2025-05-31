# Configuration management using Pydantic settings
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "AI Productivity App"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./data/app.db"
    database_echo: bool = False

    # Security
    secret_key: str = "change-this-in-production-use-secrets-module"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Authentication
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Registration
    registration_enabled: bool = True
    invite_codes: str = "code1,code2,code3"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # API Keys (for future phases)
    openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None

    @property
    def effective_secret_key(self) -> str:
        """Return JWT secret key if set, otherwise fall back to main secret"""
        return self.jwt_secret_key or self.secret_key

    @property
    def invite_codes_list(self) -> list[str]:
        """Return list of valid invite codes"""
        return [code.strip() for code in self.invite_codes.split(",") if code.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
