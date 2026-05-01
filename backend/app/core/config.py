from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    paraworks_env: str = 'local'
    paraworks_demo_mode: bool = True
    database_url: str = 'postgresql+psycopg://paraworks:paraworks@localhost:5432/paraworks'
    redis_url: str = 'redis://localhost:6379/0'
    celery_task_always_eager: bool = True
    openai_api_key: str | None = None
    openai_embedding_model: str = 'text-embedding-3-small'
    openai_embedding_dimensions: int = 1536
    openai_embedding_timeout_seconds: float = 30.0
    rag_use_pgvector_search: bool = False
    slack_bot_token: str | None = None
    slack_channel_ids: str = ''
    slack_workspace_url: str = 'https://slack.com'


@lru_cache
def get_settings() -> Settings:
    return Settings()
