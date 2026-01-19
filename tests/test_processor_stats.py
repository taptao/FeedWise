"""测试 processor 模块的统计和辅助函数."""

from sqlalchemy.ext.asyncio import AsyncSession

from feedwise.core.processor import (
    get_failed_articles,
    get_process_stats,
    reset_failed_to_pending,
)
from feedwise.models.article import Article


class TestGetProcessStats:
    """测试 get_process_stats 函数."""

    async def test_returns_correct_pending_count(
        self, async_session: AsyncSession, sample_articles: list[Article]
    ) -> None:
        """当有 synced/pending_fetch/pending_analysis 状态的文章时，计数正确."""
        # Arrange: sample_articles 包含 1 个 synced, 1 个 pending_fetch, 1 个 pending_analysis
        # Act
        stats = await get_process_stats(async_session)
        # Assert
        assert stats.synced == 2  # synced + pending_fetch
        assert stats.pending_analysis == 1

    async def test_returns_correct_done_count(
        self, async_session: AsyncSession, sample_articles: list[Article]
    ) -> None:
        """当有 done 状态的文章时，done 计数正确."""
        stats = await get_process_stats(async_session)
        assert stats.done == 1

    async def test_returns_correct_failed_count(
        self, async_session: AsyncSession, sample_articles: list[Article]
    ) -> None:
        """当有 failed 状态的文章时，failed 计数正确."""
        stats = await get_process_stats(async_session)
        assert stats.failed == 1

    async def test_returns_correct_total(
        self, async_session: AsyncSession, sample_articles: list[Article]
    ) -> None:
        """total 应等于所有状态的总和."""
        stats = await get_process_stats(async_session)
        assert stats.total == 5

    async def test_returns_zero_when_no_articles(
        self, async_session: AsyncSession
    ) -> None:
        """当没有文章时，所有计数为 0."""
        stats = await get_process_stats(async_session)
        assert stats.synced == 0
        assert stats.fetching == 0
        assert stats.pending_analysis == 0
        assert stats.analyzing == 0
        assert stats.done == 0
        assert stats.failed == 0
        assert stats.total == 0


class TestGetFailedArticles:
    """测试 get_failed_articles 函数."""

    async def test_returns_failed_articles_with_details(
        self, async_session: AsyncSession, sample_articles: list[Article]
    ) -> None:
        """返回失败文章的详细信息."""
        items, total = await get_failed_articles(async_session)
        assert total == 1
        assert len(items) == 1
        assert items[0]["article_id"] == "article-004"
        assert items[0]["title"] == "Article 4 - Failed"
        assert items[0]["stage"] == "fetch"
        assert items[0]["error"] == "Connection timeout"

    async def test_returns_empty_when_no_failed(
        self, async_session: AsyncSession, sample_feed: None
    ) -> None:
        """当没有失败文章时，返回空列表."""
        # 创建一个没有失败状态的文章
        article = Article(
            id="article-ok",
            feed_id="feed-001",
            title="OK Article",
            process_status="done",
        )
        async_session.add(article)
        await async_session.commit()

        items, total = await get_failed_articles(async_session)
        assert total == 0
        assert len(items) == 0

    async def test_pagination_works(
        self, async_session: AsyncSession, sample_feed: None
    ) -> None:
        """分页功能正常工作."""
        # 创建多个失败文章
        for i in range(5):
            article = Article(
                id=f"failed-{i}",
                feed_id="feed-001",
                title=f"Failed Article {i}",
                process_status="failed",
                process_error="Error",
            )
            async_session.add(article)
        await async_session.commit()

        # 第一页
        items, total = await get_failed_articles(async_session, page=1, limit=2)
        assert total == 5
        assert len(items) == 2

        # 第二页
        items, total = await get_failed_articles(async_session, page=2, limit=2)
        assert total == 5
        assert len(items) == 2


class TestResetFailedToPending:
    """测试 reset_failed_to_pending 函数."""

    async def test_resets_fetch_failed_to_pending_fetch(
        self, async_session: AsyncSession, sample_feed: None
    ) -> None:
        """fetch 阶段失败的文章重置为 pending_fetch."""
        article = Article(
            id="fetch-failed",
            feed_id="feed-001",
            title="Fetch Failed",
            process_status="failed",
            process_stage="fetch",
            process_error="Timeout",
        )
        async_session.add(article)
        await async_session.commit()

        count = await reset_failed_to_pending(async_session)

        assert count == 1
        await async_session.refresh(article)
        assert article.process_status == "pending_fetch"
        assert article.process_error is None
        assert article.process_stage is None

    async def test_resets_analysis_failed_to_pending_analysis(
        self, async_session: AsyncSession, sample_feed: None
    ) -> None:
        """analysis 阶段失败的文章重置为 pending_analysis."""
        article = Article(
            id="analysis-failed",
            feed_id="feed-001",
            title="Analysis Failed",
            process_status="failed",
            process_stage="analysis",
            process_error="LLM Error",
        )
        async_session.add(article)
        await async_session.commit()

        count = await reset_failed_to_pending(async_session)

        assert count == 1
        await async_session.refresh(article)
        assert article.process_status == "pending_analysis"

    async def test_returns_zero_when_no_failed(
        self, async_session: AsyncSession
    ) -> None:
        """当没有失败文章时，返回 0."""
        count = await reset_failed_to_pending(async_session)
        assert count == 0
