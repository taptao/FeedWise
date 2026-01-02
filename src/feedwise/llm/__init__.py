"""LLM 抽象层."""

from feedwise.llm.analyzer import AnalysisResult, ArticleAnalyzer
from feedwise.llm.base import LLMConfig, LLMProvider, Message
from feedwise.llm.factory import create_llm_provider
from feedwise.llm.ollama import OllamaProvider
from feedwise.llm.openai import OpenAIProvider

__all__ = [
    "AnalysisResult",
    "ArticleAnalyzer",
    "LLMConfig",
    "LLMProvider",
    "Message",
    "OllamaProvider",
    "OpenAIProvider",
    "create_llm_provider",
]

