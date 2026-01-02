"""文章分析器."""

import json
from collections.abc import AsyncIterator

from pydantic import BaseModel

from feedwise.llm.base import LLMProvider, Message

SYSTEM_PROMPT = """你是一个专业的文章分析助手，擅长快速理解和评估文章价值。

## 任务
分析用户提供的文章，返回结构化的分析结果。

## 输出格式（严格 JSON）
{
  "summary": "2-3句话的文章摘要，使用文章原语言",
  "key_points": ["要点1", "要点2", "要点3"],
  "value_score": 7.5,
  "reading_time": 5,
  "language": "zh",
  "tags": ["技术", "AI", "趋势"]
}

## 价值评分标准 (1-10)
- 9-10: 突破性内容、重大新闻、深度原创分析
- 7-8: 高质量技术文章、有价值的见解
- 5-6: 一般性信息、常规更新
- 3-4: 旧闻、重复内容、广告软文
- 1-2: 垃圾内容、无实质内容

## 注意事项
- 摘要使用文章原语言
- 关键要点保持简洁，3-5个
- 阅读时间以分钟为单位
- 标签 3-5 个，反映主题
- language 只能是 "zh" 或 "en"
- 只返回 JSON，不要其他内容"""

USER_PROMPT_TEMPLATE = """请分析以下文章：

**标题**：{title}
**来源**：{feed_name}

**正文**：
{content}"""


class AnalysisResult(BaseModel):
    """文章分析结果."""

    summary: str
    key_points: list[str]
    value_score: float
    reading_time: int
    language: str
    tags: list[str]


class ArticleAnalyzer:
    """文章分析器."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def analyze(
        self,
        title: str,
        content: str,
        feed_name: str = "",
    ) -> AnalysisResult:
        """分析文章，返回结构化结果."""
        messages = self._build_messages(title, content, feed_name)
        response = await self.provider.chat(messages)

        # 解析 JSON 响应
        return self._parse_response(response)

    async def analyze_stream(
        self,
        title: str,
        content: str,
        feed_name: str = "",
    ) -> AsyncIterator[str]:
        """流式分析，逐步返回响应."""
        messages = self._build_messages(title, content, feed_name)
        async for chunk in self.provider.chat_stream(messages):
            yield chunk

    def _build_messages(
        self,
        title: str,
        content: str,
        feed_name: str,
    ) -> list[Message]:
        """构建对话消息."""
        # 限制内容长度，避免超过 token 限制
        max_content_length = 8000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n\n[内容已截断...]"

        user_content = USER_PROMPT_TEMPLATE.format(
            title=title,
            feed_name=feed_name or "未知来源",
            content=content,
        )

        return [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=user_content),
        ]

    def _parse_response(self, response: str) -> AnalysisResult:
        """解析 LLM 响应."""
        # 尝试提取 JSON
        response = response.strip()

        # 移除可能的 markdown 代码块标记
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            data = json.loads(response)
            return AnalysisResult(
                summary=data.get("summary", ""),
                key_points=data.get("key_points", []),
                value_score=float(data.get("value_score", 5.0)),
                reading_time=int(data.get("reading_time", 5)),
                language=data.get("language", "zh"),
                tags=data.get("tags", []),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # 解析失败，返回默认值
            return AnalysisResult(
                summary="分析失败，请稍后重试",
                key_points=[],
                value_score=5.0,
                reading_time=5,
                language="zh",
                tags=[],
            )

