from __future__ import annotations

from typing import Annotated

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # ── App ────────────────────────────────────────────────────────────────────
    app_name: str = 'ParaWorks'
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str  # e.g. postgresql+asyncpg://user:pass@host/db
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Azure OpenAI ───────────────────────────────────────────────────────────
    azure_openai_endpoint: str = ''
    azure_openai_api_key: str = ''
    azure_openai_api_version: str = '2025-01-01-preview'
    azure_openai_deployment_chat: str = 'gpt-4o'
    azure_openai_deployment_embedding: str = 'text-embedding-3-small'
    azure_openai_embedding_dimensions: int = 1536

    # ── Azure Content Safety ───────────────────────────────────────────────────
    azure_content_safety_endpoint: str = ''
    azure_content_safety_key: str = ''

    # ── LangSmith (optional) ───────────────────────────────────────────────────
    langsmith_tracing: bool = False
    langsmith_api_key: str = ''

    # ── Google APIs ────────────────────────────────────────────────────────────
    google_service_account_json: str = ''  # path or JSON string
    google_subject_email: str = ''  # domain-wide delegation subject

    # ── Slack ──────────────────────────────────────────────────────────────────
    slack_bot_token: str = ''
    slack_signing_secret: str = ''
    slack_app_token: str = ''  # Socket Mode용

    # ── Organization ───────────────────────────────────────────────────────────
    # 콤마 구분 복수 도메인 허용: "company.com,subsidiary.co.kr"
    allowed_email_domains: str = ''

    @field_validator('allowed_email_domains', mode='before')
    @classmethod
    def parse_domains(cls, v: object) -> str:
        if isinstance(v, list):
            return ','.join(str(d).strip().lower() for d in v if str(d).strip())
        return str(v) if v else ''

    def is_allowed_domain(self, email: str) -> bool:
        if not self.allowed_email_domains:
            return True  # 미설정 시 모든 도메인 허용
        domain = email.split('@')[-1].lower()
        return domain in {d.strip() for d in self.allowed_email_domains.split(',') if d.strip()}

    # ── Embedding ──────────────────────────────────────────────────────────────
    # "azure_openai" | "sentence_transformers"
    embedding_backend: str = 'azure_openai'
    local_embedding_model: str = 'intfloat/multilingual-e5-large'

    # ── Chunking ───────────────────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64

    # ── RAG retrieval ──────────────────────────────────────────────────────────
    retrieval_top_k: int = 8

    # ── CORS ───────────────────────────────────────────────────────────────────
    # 콤마 구분 복수 URL: "http://localhost:3000,https://app.example.com"
    allowed_origins: str = 'http://localhost:3000'

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_origins(cls, v: object) -> str:
        if isinstance(v, list):
            return ','.join(str(o) for o in v)
        return str(v)


settings = Settings()  # type: ignore[call-arg]
