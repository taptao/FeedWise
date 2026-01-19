"""E2E 测试：完整处理流程."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from feedwise.core.processor import ProcessEngine, ProcessStatus
from feedwise.fetcher.extractor import FullTextResult
from feedwise.llm import AnalysisResult
from feedwise.models.article import Article
from feedwise.models.feed import Feed


@pytest.fixture
async def e2e_feed(async_session: AsyncSession) -> Feed:
    """创建 E2E 测试用的 Feed."""
    feed = Feed(
        id="e2e-feed",
        title="E2E Test Feed",
        url="https://example.com/feed.xml",
        fetch_full_text="always",
    )
    async_session.add(feed)
    await async_session.commit()
    return feed


@pytest.fixture
async def e2e_article(async_session: AsyncSession, e2e_feed: Feed) -> Article:
    """创建 E2E 测试用的文章."""
    article = Article(
        id="e2e-article-1",
        feed_id=e2e_feed.id,
        title="E2E Test Article",
        url="https://example.com/article-1",
        content_text="Short summary",
        process_status=ProcessStatus.SYNCED,
    )
    async_session.add(article)
    await async_session.commit()
    return article


class TestDoFetch:
    """测试 _do_fetch 方法."""

    async def test_fetch_success_updates_status(
        self, async_session: AsyncSession, e2e_article: Article, e2e_feed: Feed
    ) -> None:
        """抓取成功时更新状态为 pending_analysis."""
        engine = ProcessEngine()

        # Mock extractor
        mock_result = FullTextResult(
            success=True,
            content="Full article content here",
            word_count=100,
        )
        engine._extractor = MagicMock()
        engine._extractor.fetch = AsyncMock(return_value=mock_result)

        await engine._do_fetch(async_session, e2e_article)

        await async_session.refresh(e2e_article)
        assert e2e_article.process_status == ProcessStatus.PENDING_ANALYSIS
        assert e2e_article.full_content == "Full article content here"
        assert e2e_article.fetch_status == "success"

    async def test_fetch_failure_updates_status(
        self, async_session: AsyncSession, e2e_article: Article, e2e_feed: Feed
    ) -> None:
        """抓取失败时更新状态为 failed."""
        engine = ProcessEngine()

        mock_result = FullTextResult(
            success=False,
            error="Connection timeout",
        )
        engine._extractor = MagicMock()
        engine._extractor.fetch = AsyncMock(return_value=mock_result)

        await engine._do_fetch(async_session, e2e_article)

        await async_session.refresh(e2e_article)
        assert e2e_article.process_status == ProcessStatus.FAILED
        assert e2e_article.process_stage == "fetch"
        assert e2e_article.process_error == "Connection timeout"

    async def test_skip_fetch_when_no_url(
        self, async_session: AsyncSession, e2e_feed: Feed
    ) -> None:
        """无 URL 时跳过抓取."""
        article = Article(
            id="no-url-article",
            feed_id=e2e_feed.id,
            title="No URL Article",
            url=None,
            process_status=ProcessStatus.SYNCED,
        )
        async_session.add(article)
        await async_session.commit()

        engine = ProcessEngine()
        await engine._do_fetch(async_session, article)

        await async_session.refresh(article)
        assert article.process_status == ProcessStatus.PENDING_ANALYSIS
        assert article.fetch_status == "skipped"


class TestDoAnalysis:
    """测试 _do_analysis 方法."""

    async def test_analysis_success_updates_status(
        self, async_session: AsyncSession, e2e_feed: Feed
    ) -> None:
        """分析成功时更新状态为 done."""
        article = Article(
            id="analysis-article",
            feed_id=e2e_feed.id,
            title="Analysis Test Article",
            full_content="Full content for analysis",
            process_status=ProcessStatus.PENDING_ANALYSIS,
        )
        async_session.add(article)
        await async_session.commit()

        engine = ProcessEngine()

        # Mock LLM
        mock_analysis = AnalysisResult(
            summary="Test summary",
            key_points=["Point 1", "Point 2"],
            value_score=8,
            reading_time=5,
            language="zh",
            tags=["test", "e2e"],
        )

        with (
            patch("feedwise.core.processor.get_settings") as mock_settings,
            patch("feedwise.core.processor.create_llm_provider"),
            patch("feedwise.core.processor.ArticleAnalyzer") as mock_analyzer_cls,
        ):
            mock_settings.return_value = MagicMock(
                llm_provider="openai",
                openai_model="gpt-4",
            )
            mock_analyzer = MagicMock()
            mock_analyzer.analyze = AsyncMock(return_value=mock_analysis)
            mock_analyzer_cls.return_value = mock_analyzer

            await engine._do_analysis(async_session, article)

        await async_session.refresh(article)
        assert article.process_status == ProcessStatus.DONE

    async def test_analysis_failure_updates_status(
        self, async_session: AsyncSession, e2e_feed: Feed
    ) -> None:
        """分析失败时更新状态为 failed."""
        article = Article(
            id="analysis-fail-article",
            feed_id=e2e_feed.id,
            title="Analysis Fail Article",
            full_content="Content",
            process_status=ProcessStatus.PENDING_ANALYSIS,
        )
        async_session.add(article)
        await async_session.commit()

        engine = ProcessEngine()

        with (
            patch("feedwise.core.processor.get_settings") as mock_settings,
            patch("feedwise.core.processor.create_llm_provider"),
            patch("feedwise.core.processor.ArticleAnalyzer") as mock_analyzer_cls,
        ):
            mock_settings.return_value = MagicMock(llm_provider="openai")
            mock_analyzer = MagicMock()
            mock_analyzer.analyze = AsyncMock(side_effect=Exception("LLM Error"))
            mock_analyzer_cls.return_value = mock_analyzer

            await engine._do_analysis(async_session, article)

        await async_session.refresh(article)
        assert article.process_status == ProcessStatus.FAILED
        assert article.process_stage == "analysis"
        assert "LLM Error" in (article.process_error or "")

    async def test_skip_analysis_when_no_content(
        self, async_session: AsyncSession, e2e_feed: Feed
    ) -> None:
        """无内容时跳过分析."""
        article = Article(
            id="no-content-article",
            feed_id=e2e_feed.id,
            title="No Content Article",
            full_content=None,
            content_text=None,
            process_status=ProcessStatus.PENDING_ANALYSIS,
        )
        async_session.add(article)
        await async_session.commit()

        engine = ProcessEngine()
        await engine._do_analysis(async_session, article)

        await async_session.refresh(article)
        assert article.process_status == ProcessStatus.DONE
