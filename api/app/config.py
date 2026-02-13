"""
Application configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Database
    database_url: str

    # Supabase
    supabase_url: str = ""
    supabase_jwt_aud: str = "authenticated"
    supabase_jwt_secret: str = ""

    # External APIs
    google_maps_api_key: str = ""
    openai_api_key: str = ""

    # CORS
    cors_allowed_origins: str = "http://localhost:3000"

    # App
    debug: bool = False
    app_url: str = "https://pyxten.vercel.app"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_professional_monthly: str = ""
    stripe_price_professional_annual: str = ""
    stripe_price_empresarial_monthly: str = ""
    stripe_price_empresarial_annual: str = ""

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
