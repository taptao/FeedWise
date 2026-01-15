"""统一处理引擎 - 全文抓取 + AI 分析."""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from feedwise.config import get_settings
from feedwise.fetcher.detector import ContentDetector
from feedwise.fetcher.extractor import FullTextExtractor
from feedwise.llm import ArticleAnalyzer, create_llm_provider
from feedwise.models.analysis import ArticleAnalysis
from feedwise.models.article import Article
from feedwise.models.database import async_session_maker
from feedwise.models.feed import Feed

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


# 处理状态常量
class ProcessStatus:
    """处理状态枚举."""

    SYNCED = "synced"
    PENDING_FETCH = "pending_fetch"
    FETCHING = "fetching"
    PENDING_ANALYSIS = "pending_analysis"
    ANALYZING = "analyzing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ProcessStats:
    """处理统计."""

    pending: int = 0
    processing: int = 0
    done: int = 0
    failed: int = 0
    total: int = 0


@dataclass
class ProcessProgress:
    """处理进度."""

    status: str = "idle"  # idle | running | paused
    total: int = 0
    completed: int = 0
    failed: int = 0
    current_article: str | None = None
    current_stage: str | None = None  # fetch | analysis
    started_at: datetime | None = None


# 全局状态
_ws_connections: set["WebSocket"] = set()
_engine: "ProcessEngine | None" = None
_progress = ProcessProgress()


def get_engine() -> "ProcessEngine | None":
    """获取处理引擎实例."""
    return _engine


def get_progress() -> ProcessProgress:
    """获取当前进度."""
    return _progress


async def broadcast(message: dict[str, Any]) -> None:
    """广播消息到所有 WebSocket 连接."""
    if not _ws_connections:
        return

    data = json.dumps(message, ensure_ascii=False, default=str)
    dead_connections: set[WebSocket] = set()

    for ws in _ws_connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead_connections.add(ws)

    # 清理断开的连接
    _ws_connections.difference_update(dead_connections)


def register_ws(ws: "WebSocket") -> None:
    """注册 WebSocket 连接."""
    _ws_connections.add(ws)


def unregister_ws(ws: "WebSocket") -> None:
    """注销 WebSocket 连接."""
    _ws_connections.discard(ws)


class ProcessEngine:
    """统一处理引擎."""

    def __init__(self) -> None:
        self._running = False
        self._paused = False
        self._detector = ContentDetector()
        self._extractor = FullTextExtractor()
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        """是否正在运行."""
        return self._running and not self._paused

    async def start(self, batch_size: int = 50) -> None:
        """启动处理循环."""
        global _engine, _progress

        if self._running:
            logger.warning("处理引擎已在运行")
            return

        _engine = self
        self._running = True
        self._paused = False

        _progress.status = "running"
        _progress.started_at = datetime.now(UTC)
        _progress.completed = 0
        _progress.failed = 0

        logger.info("处理引擎启动")
        await broadcast({"type": "started", "data": {}})

        try:
            await self._run_loop(batch_size)
        finally:
            self._running = False
            _progress.status = "idle"
            _progress.current_article = None
            _progress.current_stage = None

    def pause(self) -> None:
        """暂停处理."""
        global _progress
        self._paused = True
        _progress.status = "paused"
        logger.info("处理引擎暂停")

    def resume(self) -> None:
        """恢复处理."""
        global _progress
        self._paused = False
        _progress.status = "running"
        logger.info("处理引擎恢复")

    def stop(self) -> None:
        """停止处理."""
        self._running = False
        self._paused = False
        logger.info("处理引擎停止")

    async def _run_loop(self, batch_size: int) -> None:
        """处理循环."""
        global _progress

        async with async_session_maker()() as session:
            # 统计待处理数量
            pending_count = await self._count_pending(session)
            _progress.total = pending_count

            await broadcast(
                {
                    "type": "progress",
                    "data": {
                        "total": _progress.total,
                        "completed": 0,
                        "failed": 0,
                        "current": None,
                    },
                }
            )

            while self._running and not self._paused:
                # 获取下一批待处理文章
                articles = await self._get_pending_articles(session, batch_size)

                if not articles:
                    logger.info("没有待处理的文章")
                    break

                for article in articles:
                    if not self._running or self._paused:
                        break

                    await self._process_one(session, article)

            # 完成
            await broadcast(
                {
                    "type": "completed",
                    "data": {
                        "total": _progress.total,
                        "success": _progress.completed,
                        "failed": _progress.failed,
                    },
                }
            )

    async def _count_pending(self, session: AsyncSession) -> int:
        """统计待处理文章数量."""
        stmt = select(Article).where(
            Article.process_status.in_(  # type: ignore[union-attr]
                [
                    ProcessStatus.SYNCED,
                    ProcessStatus.PENDING_FETCH,
                    ProcessStatus.PENDING_ANALYSIS,
                ]
            )
        )
        result = await session.execute(stmt)
        return len(result.scalars().all())

    async def _get_pending_articles(
        self, session: AsyncSession, limit: int
    ) -> list[Article]:
        """获取待处理文章."""
        stmt = (
            select(Article)
            .where(
                Article.process_status.in_(  # type: ignore[union-attr]
                    [
                        ProcessStatus.SYNCED,
                        ProcessStatus.PENDING_FETCH,
                        ProcessStatus.PENDING_ANALYSIS,
                    ]
                )
            )
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _process_one(self, session: AsyncSession, article: Article) -> None:
        """处理单篇文章."""
        global _progress

        _progress.current_article = article.title[:50]

        try:
            # 根据当前状态决定下一步
            if article.process_status in [
                ProcessStatus.SYNCED,
                ProcessStatus.PENDING_FETCH,
            ]:
                await self._do_fetch(session, article)

            if article.process_status == ProcessStatus.PENDING_ANALYSIS:
                await self._do_analysis(session, article)

        except Exception as e:
            logger.exception(f"处理文章失败: {article.title}")
            article.process_status = ProcessStatus.FAILED
            article.process_error = str(e)
            await session.commit()
            _progress.failed += 1

        # 广播进度
        await broadcast(
            {
                "type": "progress",
                "data": {
                    "total": _progress.total,
                    "completed": _progress.completed,
                    "failed": _progress.failed,
                    "current": _progress.current_article,
                    "stage": _progress.current_stage,
                },
            }
        )

    async def _do_fetch(self, session: AsyncSession, article: Article) -> None:
        """执行全文抓取."""
        global _progress
        _progress.current_stage = "fetch"

        # 更新状态为 fetching
        article.process_status = ProcessStatus.FETCHING
        await session.commit()

        # 检查是否有 URL
        if not article.url:
            article.process_status = ProcessStatus.PENDING_ANALYSIS
            article.fetch_status = "skipped"
            await session.commit()
            logger.info(f"跳过抓取 (无 URL): {article.title}")
            return

        # 获取 Feed 配置
        feed = await session.get(Feed, article.feed_id)

        # 判断是否需要抓取
        should_fetch = await self._should_fetch(article, feed)
        if not should_fetch:
            article.process_status = ProcessStatus.PENDING_ANALYSIS
            article.fetch_status = "skipped"
            await session.commit()
            logger.info(f"跳过抓取 (配置): {article.title}")
            return

        # 执行抓取
        result = await self._extractor.fetch(article.url)

        if result.success and result.content:
            article.full_content = result.content
            article.content_source = "fetched"
            article.fetch_status = "success"
            article.process_status = ProcessStatus.PENDING_ANALYSIS
            logger.info(f"抓取成功: {article.title} ({result.word_count} 字)")
        else:
            article.fetch_status = "failed"
            article.process_status = ProcessStatus.FAILED
            article.process_stage = "fetch"
            article.process_error = result.error or "未知错误"
            _progress.failed += 1
            logger.warning(f"抓取失败: {article.title} - {result.error}")

            await broadcast(
                {
                    "type": "item_failed",
                    "data": {
                        "article_id": article.id,
                        "title": article.title,
                        "stage": "fetch",
                        "error": result.error,
                    },
                }
            )

        await session.commit()

    async def _should_fetch(self, article: Article, feed: Feed | None) -> bool:
        """判断是否需要抓取全文."""
        if feed:
            if feed.fetch_full_text == "always":
                return True
            if feed.fetch_full_text == "never":
                return False

        # auto 模式：智能检测
        return self._detector.needs_full_content(
            title=article.title,
            content=article.content_text or "",
        )

    async def _do_analysis(self, session: AsyncSession, article: Article) -> None:
        """执行 AI 分析."""
        global _progress
        _progress.current_stage = "analysis"

        # 更新状态为 analyzing
        article.process_status = ProcessStatus.ANALYZING
        await session.commit()

        # 获取内容
        content = article.full_content or article.content_text or ""
        if not content:
            article.process_status = ProcessStatus.DONE
            _progress.completed += 1
            await session.commit()
            logger.info(f"跳过分析 (无内容): {article.title}")
            return

        try:
            # 创建 LLM Provider
            settings = get_settings()
            provider = create_llm_provider(settings)
            analyzer = ArticleAnalyzer(provider)

            # 执行分析
            result = await analyzer.analyze(
                title=article.title,
                content=content,
                feed_name="",
            )

            # 检查是否已有分析结果
            stmt = select(ArticleAnalysis).where(
                ArticleAnalysis.article_id == article.id
            )
            existing_result = await session.execute(stmt)
            existing = existing_result.scalar_one_or_none()

            model_name = (
                settings.openai_model
                if settings.llm_provider == "openai"
                else settings.ollama_model
            )

            if existing:
                existing.summary = result.summary
                existing.key_points = json.dumps(result.key_points, ensure_ascii=False)
                existing.value_score = result.value_score
                existing.reading_time = result.reading_time
                existing.language = result.language
                existing.tags = json.dumps(result.tags, ensure_ascii=False)
                existing.model_used = model_name
            else:
                analysis = ArticleAnalysis(
                    article_id=article.id,
                    summary=result.summary,
                    key_points=json.dumps(result.key_points, ensure_ascii=False),
                    value_score=result.value_score,
                    reading_time=result.reading_time,
                    language=result.language,
                    tags=json.dumps(result.tags, ensure_ascii=False),
                    model_used=model_name,
                )
                session.add(analysis)

            article.process_status = ProcessStatus.DONE
            _progress.completed += 1
            logger.info(f"分析完成: {article.title}")

            await broadcast(
                {
                    "type": "item_done",
                    "data": {
                        "article_id": article.id,
                        "title": article.title,
                    },
                }
            )

        except Exception as e:
            article.process_status = ProcessStatus.FAILED
            article.process_stage = "analysis"
            article.process_error = str(e)
            _progress.failed += 1
            logger.exception(f"分析失败: {article.title}")

            await broadcast(
                {
                    "type": "item_failed",
                    "data": {
                        "article_id": article.id,
                        "title": article.title,
                        "stage": "analysis",
                        "error": str(e),
                    },
                }
            )

        await session.commit()


async def get_process_stats(session: AsyncSession) -> ProcessStats:
    """获取处理统计."""
    stats = ProcessStats()

    # pending: synced + pending_fetch + pending_analysis
    pending_stmt = select(Article).where(
        Article.process_status.in_(  # type: ignore[union-attr]
            [
                ProcessStatus.SYNCED,
                ProcessStatus.PENDING_FETCH,
                ProcessStatus.PENDING_ANALYSIS,
            ]
        )
    )
    pending_result = await session.execute(pending_stmt)
    stats.pending = len(pending_result.scalars().all())

    # processing: fetching + analyzing
    processing_stmt = select(Article).where(
        Article.process_status.in_(  # type: ignore[union-attr]
            [
                ProcessStatus.FETCHING,
                ProcessStatus.ANALYZING,
            ]
        )
    )
    processing_result = await session.execute(processing_stmt)
    stats.processing = len(processing_result.scalars().all())

    # done
    done_stmt = select(Article).where(Article.process_status == ProcessStatus.DONE)
    done_result = await session.execute(done_stmt)
    stats.done = len(done_result.scalars().all())

    # failed
    failed_stmt = select(Article).where(Article.process_status == ProcessStatus.FAILED)
    failed_result = await session.execute(failed_stmt)
    stats.failed = len(failed_result.scalars().all())

    stats.total = stats.pending + stats.processing + stats.done + stats.failed
    return stats


async def get_failed_articles(
    session: AsyncSession, page: int = 1, limit: int = 20
) -> tuple[list[dict[str, str | None]], int]:
    """获取失败的文章列表."""
    # 总数
    count_stmt = select(Article).where(Article.process_status == ProcessStatus.FAILED)
    count_result = await session.execute(count_stmt)
    total = len(count_result.scalars().all())

    # 分页
    offset = (page - 1) * limit
    stmt = (
        select(Article)
        .where(Article.process_status == ProcessStatus.FAILED)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    articles = result.scalars().all()

    items: list[dict[str, str | None]] = []
    for article in articles:
        feed = await session.get(Feed, article.feed_id)
        items.append(
            {
                "article_id": article.id,
                "title": article.title,
                "url": article.url,
                "feed_title": feed.title if feed else "未知来源",
                "stage": article.process_stage,
                "error": article.process_error,
            }
        )

    return items, total


async def reset_failed_to_pending(session: AsyncSession) -> int:
    """重置失败状态为待处理."""
    stmt = select(Article).where(Article.process_status == ProcessStatus.FAILED)
    result = await session.execute(stmt)
    articles = result.scalars().all()

    count = 0
    for article in articles:
        # 根据失败阶段决定重置到哪个状态
        if article.process_stage == "fetch":
            article.process_status = ProcessStatus.PENDING_FETCH
        else:
            article.process_status = ProcessStatus.PENDING_ANALYSIS
        article.process_error = None
        article.process_stage = None
        count += 1

    await session.commit()
    logger.info(f"重置了 {count} 篇失败文章")
    return count
