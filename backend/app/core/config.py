from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = Field(default="FinEx", alias="FINEX_APP_NAME")
    env: str = Field(default="development", alias="FINEX_ENV")
    database_url: str = Field(
        default="sqlite:///./data/local/finex.db",
        alias="FINEX_DATABASE_URL",
    )
    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="FINEX_ALLOWED_ORIGINS",
    )
    gmail_credentials_path: str = Field(
        default="data/local/gmail_credentials.json",
        alias="GMAIL_CREDENTIALS_PATH",
    )
    gmail_token_path: str = Field(
        default="data/local/gmail_token.json",
        alias="GMAIL_TOKEN_PATH",
    )
    gmail_redirect_uri: str = Field(
        default="http://127.0.0.1:8000/api/v1/gmail/callback",
        alias="GMAIL_REDIRECT_URI",
    )
    gmail_scopes: str = Field(
        default="https://www.googleapis.com/auth/gmail.readonly",
        alias="GMAIL_SCOPES",
    )
    gmail_default_query: str = Field(
        default="newer_than:30d",
        alias="GMAIL_DEFAULT_QUERY",
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
