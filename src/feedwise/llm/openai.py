"""OpenAI LLM Provider."""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from feedwise.llm.base import LLMConfig, LLMProvider, Message


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider（支持所有 OpenAI 兼容接口）."""

    def __init__(
        self,
        config: LLMConfig,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(self, messages: list[Message]) -> str:
        """同步对话，返回完整响应."""
        openai_messages: list[dict[str, Any]] = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        content = response.choices[0].message.content
        return content or ""

    async def chat_stream(self, messages: list[Message]) -> AsyncIterator[str]:
        """流式对话，逐步返回响应."""
        openai_messages: list[dict[str, Any]] = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        stream = await self.client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
