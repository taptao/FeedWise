"""应用配置管理."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # FreshRSS 配置
    freshrss_url: str = ""
    freshrss_username: str = ""
    freshrss_api_password: str = ""

    # LLM 配置
    llm_provider: Literal["openai", "ollama"] = "openai"

    # OpenAI 配置
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Ollama 配置
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # 应用配置
    database_url: str = "sqlite+aiosqlite:///./feedwise.db"
    sync_interval_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    """获取应用配置（带缓存）."""
    return Settings()
