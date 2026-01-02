"""全文抓取任务执行器."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from feedwise.fetcher.detector import ContentDetector
from feedwise.fetcher.extractor import FullTextExtractor
from feedwise.models.article import Article
from feedwise.models.feed import Feed

logger = logging.getLogger(__name__)


@dataclass
class FetchError:
    """抓取错误记录."""

    article_id: str
    title: str
    url: str
    feed_title: str
    error: str
    failed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FetchBatchStatus:
    """批量抓取状态."""

    batch_id: str
    total: int
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    status: str = "running"  # running | completed
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    current_article: str | None = None
    errors: list[FetchError] = field(default_factory=list)


# 全局状态存储
_fetch_status: dict[str, FetchBatchStatus] = {}
_current_batch_id: str | None = None


def get_current_batch_id() -> str | None:
    """获取当前正在运行的批次 ID."""
    return _current_batch_id


def get_batch_status(batch_id: str) -> FetchBatchStatus | None:
    """获取指定批次的状态."""
    return _fetch_status.get(batch_id)


def get_latest_batch_status() -> FetchBatchStatus | None:
    """获取最近一次批次状态."""
    if not _fetch_status:
        return None
    latest_id = max(_fetch_status.keys())
    return _fetch_status[latest_id]


class FetchTaskRunner:
    """全文抓取任务执行器."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.detector = ContentDetector()
        self.extractor = FullTextExtractor()

    async def get_pending_count(self) -> int:
        """获取待抓取文章数量."""
        stmt = select(Article).where(Article.fetch_status == "pending")
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def get_stats(self) -> dict[str, int]:
        """获取各状态文章数量统计."""
        stats: dict[str, int] = {
            "pending": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
        }

        # 统计各状态
        for status_value in ["pending", "success", "failed", "skipped"]:
            stmt = select(Article).where(Article.fetch_status == status_value)
            result = await self.session.execute(stmt)
            stats[status_value] = len(result.scalars().all())

        stats["total"] = sum(stats.values())
        return stats

    async def get_failed_articles(
        self,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[dict[str, str | None]], int]:
        """获取抓取失败的文章列表."""
        # 获取总数
        count_stmt = select(Article).where(Article.fetch_status == "failed")
        count_result = await self.session.execute(count_stmt)
        total = len(count_result.scalars().all())

        # 分页查询
        offset = (page - 1) * limit
        stmt = (
            select(Article)
            .where(Article.fetch_status == "failed")
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        articles = result.scalars().all()

        items: list[dict[str, str | None]] = []
        for article in articles:
            # 获取 Feed 信息
            feed = await self.session.get(Feed, article.feed_id)
            feed_title = feed.title if feed else "未知来源"

            items.append(
                {
                    "article_id": article.id,
                    "title": article.title,
                    "url": article.url,
                    "feed_title": feed_title,
                    "error": "抓取失败",  # 简化错误信息
                }
            )

        return items, total

    async def reset_failed_to_pending(self) -> int:
        """将所有失败状态重置为 pending."""
        stmt = select(Article).where(Article.fetch_status == "failed")
        result = await self.session.execute(stmt)
        articles = result.scalars().all()

        count = 0
        for article in articles:
            article.fetch_status = "pending"
            count += 1

        await self.session.commit()
        logger.info(f"重置了 {count} 篇失败文章为 pending 状态")
        return count

    async def run_batch(
        self,
        batch_size: int = 20,
        concurrency: int = 4,
    ) -> FetchBatchStatus:
        """
        批量抓取 pending 文章.

        Args:
            batch_size: 每批处理数量
            concurrency: 并发数

        Returns:
            FetchBatchStatus: 抓取结果
        """
        global _current_batch_id

        # 查询待抓取文章
        stmt = (
            select(Article).where(Article.fetch_status == "pending").limit(batch_size)
        )
        result = await self.session.execute(stmt)
        articles = result.scalars().all()

        if not articles:
            logger.info("没有待抓取的文章")
            return FetchBatchStatus(
                batch_id="empty",
                total=0,
                status="completed",
                completed_at=datetime.utcnow(),
            )

        # 创建批次状态
        batch_id = f"fetch_{int(datetime.utcnow().timestamp())}"
        status = FetchBatchStatus(
            batch_id=batch_id,
            total=len(articles),
        )
        _fetch_status[batch_id] = status
        _current_batch_id = batch_id

        logger.info(f"开始批量抓取，共 {len(articles)} 篇待处理")

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_with_semaphore(article: Article, index: int) -> None:
            async with semaphore:
                await self._fetch_single(article, status, index, len(articles))

        # 并发执行
        tasks = [
            fetch_with_semaphore(article, i) for i, article in enumerate(articles, 1)
        ]
        await asyncio.gather(*tasks)

        # 完成
        status.status = "completed"
        status.completed_at = datetime.utcnow()
        status.current_article = None
        _current_batch_id = None

        logger.info(
            f"批量抓取完成: 成功={status.completed}, "
            f"失败={status.failed}, 跳过={status.skipped}"
        )

        return status

    async def _fetch_single(
        self,
        article: Article,
        status: FetchBatchStatus,
        index: int,
        total: int,
    ) -> None:
        """抓取单篇文章."""
        status.current_article = f"[{index}/{total}] {article.title[:30]}..."

        try:
            # 检查是否有 URL
            if not article.url:
                article.fetch_status = "skipped"
                status.skipped += 1
                logger.info(f"[{index}/{total}] 跳过: {article.title} (无 URL)")
                await self.session.commit()
                return

            # 获取 Feed 配置
            feed = await self.session.get(Feed, article.feed_id)

            # 判断是否需要抓取
            should_fetch = await self._should_fetch(article, feed)
            if not should_fetch:
                article.fetch_status = "skipped"
                status.skipped += 1
                logger.info(f"[{index}/{total}] 跳过: {article.title} (配置为 never)")
                await self.session.commit()
                return

            # 执行抓取
            result = await self.extractor.fetch(article.url)

            if result.success and result.content:
                article.full_content = result.content
                article.content_source = "fetched"
                article.fetch_status = "success"
                status.completed += 1
                logger.info(
                    f"[{index}/{total}] 抓取成功: {article.title} "
                    f"({result.word_count} 字)"
                )
            else:
                article.fetch_status = "failed"
                status.failed += 1
                status.errors.append(
                    FetchError(
                        article_id=article.id,
                        title=article.title,
                        url=article.url or "",
                        feed_title=feed.title if feed else "未知",
                        error=result.error or "未知错误",
                    )
                )
                logger.warning(
                    f"[{index}/{total}] 抓取失败: {article.title} - {result.error}"
                )

            await self.session.commit()

        except Exception as e:
            article.fetch_status = "failed"
            status.failed += 1
            logger.exception(f"[{index}/{total}] 抓取异常: {article.title} - {e}")
            await self.session.commit()

    async def _should_fetch(self, article: Article, feed: Feed | None) -> bool:
        """判断是否需要抓取全文."""
        # 检查 Feed 级别设置
        if feed:
            if feed.fetch_full_text == "always":
                return True
            if feed.fetch_full_text == "never":
                return False

        # auto 模式：智能检测
        return self.detector.needs_full_content(
            title=article.title,
            content=article.content_text or "",
        )
