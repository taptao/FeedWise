"""LLM Provider 工厂."""

from feedwise.config import Settings
from feedwise.llm.base import LLMConfig, LLMProvider
from feedwise.llm.ollama import OllamaProvider
from feedwise.llm.openai import OpenAIProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    """根据配置创建 LLM Provider."""
    if settings.llm_provider == "ollama":
        config = LLMConfig(
            model=settings.ollama_model,
            temperature=0.7,
            max_tokens=2000,
        )
        return OllamaProvider(config=config, host=settings.ollama_host)

    # 默认使用 OpenAI
    config = LLMConfig(
        model=settings.openai_model,
        temperature=0.7,
        max_tokens=2000,
    )
    return OpenAIProvider(
        config=config,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
