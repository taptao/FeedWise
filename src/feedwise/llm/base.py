"""LLM 抽象基类."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel


class Message(BaseModel):
    """对话消息."""

    role: str  # "system" | "user" | "assistant"
    content: str


class LLMConfig(BaseModel):
    """LLM 配置."""

    model: str
    temperature: float = 0.7
    max_tokens: int = 2000


class LLMProvider(ABC):
    """LLM 服务提供者抽象基类."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @abstractmethod
    async def chat(self, messages: list[Message]) -> str:
        """同步对话，返回完整响应."""
        ...

    @abstractmethod
    def chat_stream(self, messages: list[Message]) -> AsyncIterator[str]:
        """流式对话，逐步返回响应."""
        ...
