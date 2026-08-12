from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://worldcup:worldcup@127.0.0.1:3306/worldcup?charset=utf8mb4"
    crawler_user_agent: str = "WorldCupResearchBot/1.0 (+mailto:data@example.com)"
    request_timeout_seconds: int = 20
    crawler_delay_seconds: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
