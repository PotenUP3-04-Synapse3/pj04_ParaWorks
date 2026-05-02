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
    openai_embedding_input_cost_per_1m_tokens: float = 0.02
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    agent_llm_enabled: bool = False
    agent_llm_provider_order: str = 'openai,gemini'
    agent_llm_openai_model: str = 'gpt-4.1-mini'
    agent_llm_gemini_model: str = 'gemini-2.5-flash'
    agent_llm_input_cost_per_1m_tokens: float = 0.15
    agent_llm_output_cost_per_1m_tokens: float = 0.60
    agent_llm_max_estimated_cost_usd: float | None = 0.001
    agent_llm_max_input_chars: int = 12000
    agent_llm_max_output_tokens: int = 512
    agent_llm_temperature: float = 0.2
    agent_llm_timeout_seconds: float = 30.0
    rag_embedding_max_estimated_cost_usd: float | None = 0.001
    rag_use_pgvector_search: bool = False
    slack_bot_token: str | None = None
    slack_channel_ids: str = ''
    slack_workspace_url: str = 'https://slack.com'
    slack_client_id: str | None = None
    slack_client_secret: str | None = None
    slack_oauth_redirect_uri: str = 'http://localhost:3000/integrations/slack/callback'
    slack_oauth_state_secret: str = 'local-development-state-secret'
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_oauth_redirect_uri: str = 'http://localhost:3000/integrations/google/callback'
    google_oauth_state_secret: str = 'local-development-google-state-secret'


@lru_cache
def get_settings() -> Settings:
    return Settings()
