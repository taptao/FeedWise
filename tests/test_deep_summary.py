"""测试精华阅读版 API."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestDeepSummaryEndpoint:
    """测试 /api/analysis/deep-summary 端点."""

    @pytest.mark.asyncio
    async def test_returns_summary_on_success(self, client: AsyncClient) -> None:
        """成功时返回精华版内容."""
        mock_response = "这是精华版内容，概括了文章的核心要点。"

        with patch(
            "feedwise.api.analysis.create_llm_provider"
        ) as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.chat = AsyncMock(return_value=mock_response)
            mock_create_provider.return_value = mock_provider

            # mock get_effective_setting 返回非 ollama
            with patch(
                "feedwise.config.get_effective_setting",
                return_value="openai",
            ):
                response = await client.post(
                    "/api/analysis/deep-summary",
                    json={
                        "article_id": "test-123",
                        "title": "测试文章",
                        "content": "这是一篇测试文章的内容。",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert data["article_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_returns_400_when_content_missing(
        self, client: AsyncClient
    ) -> None:
        """缺少内容时返回 400."""
        response = await client.post(
            "/api/analysis/deep-summary",
            json={
                "article_id": "test-123",
                "title": "测试文章",
                "content": "",
            },
        )

        assert response.status_code == 400
        assert "缺少文章内容" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_removes_think_tags_from_response(
        self, client: AsyncClient
    ) -> None:
        """移除 LLM 响应中的 <think> 标签."""
        mock_response = "<think>思考过程...</think>这是精华版内容。"

        with patch(
            "feedwise.api.analysis.create_llm_provider"
        ) as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.chat = AsyncMock(return_value=mock_response)
            mock_create_provider.return_value = mock_provider

            with patch(
                "feedwise.config.get_effective_setting",
                return_value="openai",
            ):
                response = await client.post(
                    "/api/analysis/deep-summary",
                    json={
                        "article_id": "test-123",
                        "title": "测试文章",
                        "content": "这是一篇测试文章的内容。",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert "<think>" not in data["summary"]
        assert "这是精华版内容" in data["summary"]

    @pytest.mark.asyncio
    async def test_truncates_long_content(self, client: AsyncClient) -> None:
        """长内容被截断."""
        long_content = "测试内容" * 5000  # 超过 10000 字符

        with patch(
            "feedwise.api.analysis.create_llm_provider"
        ) as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.chat = AsyncMock(return_value="精华版")
            mock_create_provider.return_value = mock_provider

            with patch(
                "feedwise.config.get_effective_setting",
                return_value="openai",
            ):
                response = await client.post(
                    "/api/analysis/deep-summary",
                    json={
                        "article_id": "test-123",
                        "title": "测试文章",
                        "content": long_content,
                    },
                )

        assert response.status_code == 200
        # 验证 chat 被调用时内容已截断
        call_args = mock_provider.chat.call_args[0][0]
        assert "[内容已截断...]" in call_args[0].content
