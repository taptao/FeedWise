"""应用配置管理."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置（环境变量）."""

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

    # 全文抓取配置
    fetch_enabled: bool = True
    fetch_concurrency: int = 4
    fetch_batch_size: int = 20
    fetch_timeout_seconds: int = 30


# 动态配置缓存
_dynamic_settings: dict[str, str | int | None] | None = None


def set_dynamic_settings(settings_dict: dict[str, str | int | None]) -> None:
    """设置动态配置缓存."""
    global _dynamic_settings
    _dynamic_settings = settings_dict


def clear_dynamic_settings() -> None:
    """清除动态配置缓存."""
    global _dynamic_settings
    _dynamic_settings = None


@lru_cache
def get_settings() -> Settings:
    """获取应用配置（带缓存）."""
    return Settings()


def get_effective_setting(key: str) -> str | int | None:
    """获取有效配置值（动态配置优先）."""
    # 优先使用动态配置
    if _dynamic_settings and key in _dynamic_settings:
        value = _dynamic_settings.get(key)
        if value is not None:
            return value

    # fallback 到环境变量配置
    settings = get_settings()
    return getattr(settings, key, None)
