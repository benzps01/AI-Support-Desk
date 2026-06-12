from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    JWT_ALGO: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7

    LLM_PROVIDER: str = "local"
    LLM_BASE_URL: str = "http://host.docker.internal:11434"
    LLM_MODEL: str = "gemma4:e4b"
    EMBED_MODEL: str = "nomic-embed-text"

settings = Settings()