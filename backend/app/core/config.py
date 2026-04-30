from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py 위치: backend/app/core/config.py → 프로젝트 루트는 4단계 위
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / '.env'),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_ENV: str = 'development'
    SECRET_KEY: str
    ALLOWED_ORIGINS: str = 'http://localhost:3000'

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(',')]

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str
    SYNC_DATABASE_URL: str

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str

    # ── MinIO ─────────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = 'localhost:9000'
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET: str = 'paraworks'
    MINIO_USE_SSL: bool = False

    # ── OpenAI ────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = 'gpt-4o'
    OPENAI_MINI_MODEL: str = 'gpt-4o-mini'
    OPENAI_EMBEDDING_MODEL: str = 'text-embedding-3-small'

    # ── LangSmith ─────────────────────────────────────────────────────────
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ''
    LANGCHAIN_PROJECT: str = 'paraworks'

    # ── Google OAuth ──────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # ── Domain Restriction ────────────────────────────────────────────────
    ALLOWED_EMAIL_DOMAINS: str = ''

    @property
    def allowed_email_domains_list(self) -> List[str]:
        if not self.ALLOWED_EMAIL_DOMAINS:
            return []
        return [d.strip().lower() for d in self.ALLOWED_EMAIL_DOMAINS.split(',')]

    # ── Slack ─────────────────────────────────────────────────────────────
    SLACK_CLIENT_ID: str = ''
    SLACK_CLIENT_SECRET: str = ''
    SLACK_REDIRECT_URI: str = ''
    SLACK_SIGNING_SECRET: str = ''

    # ── GitHub ────────────────────────────────────────────────────────────
    GITHUB_CLIENT_ID: str = ''
    GITHUB_CLIENT_SECRET: str = ''
    GITHUB_REDIRECT_URI: str = ''
    GITHUB_WEBHOOK_SECRET: str = ''

    # ── Google Drive Webhook ──────────────────────────────────────────────
    DRIVE_WEBHOOK_TOKEN: str = ''
    DRIVE_WEBHOOK_ADDRESS: str = ''

    # ── Encryption ────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str  # 32-byte base64 encoded key

    # ── JWT ───────────────────────────────────────────────────────────────
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = 'HS256'

    # ── RAG ───────────────────────────────────────────────────────────────
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 10

    # ── Validation Thresholds ─────────────────────────────────────────────
    MIN_CONFIDENCE_SCORE: float = 0.7
    MIN_FAITHFULNESS_SCORE: float = 0.85

    # ── rhwp CLI ──────────────────────────────────────────────────────────
    RHWP_BIN: str = '/usr/local/bin/rhwp'


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
