from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    paraworks_env: str = 'local'
    paraworks_demo_mode: bool = True
    database_url: str = 'postgresql+psycopg://paraworks:paraworks@localhost:5432/paraworks'
    redis_url: str = 'redis://localhost:6379/0'
    slack_bot_token: str | None = None
    slack_channel_ids: str = ''
    slack_workspace_url: str = 'https://slack.com'


@lru_cache
def get_settings() -> Settings:
    return Settings()
