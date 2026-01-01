"""Ollama LLM Provider."""

import json
from collections.abc import AsyncIterator

import httpx

from feedwise.llm.base import LLMConfig, LLMProvider, Message


class OllamaProvider(LLMProvider):
    """Ollama 本地模型 Provider."""

    def __init__(
        self,
        config: LLMConfig,
        host: str = "http://localhost:11434",
    ) -> None:
        super().__init__(config)
        self.host = host.rstrip("/")
        self._client = httpx.AsyncClient(timeout=120.0)

    async def close(self) -> None:
        """关闭客户端."""
        await self._client.aclose()

    async def chat(self, messages: list[Message]) -> str:
        """同步对话，返回完整响应."""
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        response = await self._client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("message", {}).get("content", "")

    async def chat_stream(self, messages: list[Message]) -> AsyncIterator[str]:
        """流式对话，逐步返回响应."""
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done", False):
                        break
