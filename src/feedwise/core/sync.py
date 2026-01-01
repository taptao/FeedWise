"""同步服务 - 从 FreshRSS 拉取数据."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from feedwise.core.freshrss import FreshRSSClient
from feedwise.fetcher.detector import ContentDetector
from feedwise.fetcher.extractor import FullTextExtractor
from feedwise.models.article import Article
from feedwise.models.feed import Feed
from feedwise.models.sync import SyncStatus
from feedwise.utils.html_parser import html_to_text


class SyncService:
    """同步服务."""

    def __init__(
        self,
        freshrss_client: FreshRSSClient,
        session: AsyncSession,
    ) -> None:
        self.freshrss = freshrss_client
        self.session = session
        self.detector = ContentDetector()
        self.extractor = FullTextExtractor()

    async def sync_feeds(self) -> int:
        """同步订阅源列表，返回新增/更新数量."""
        feeds = await self.freshrss.get_subscriptions()
        count = 0

        for feed in feeds:
            # 检查是否已存在
            existing = await self.session.get(Feed, feed.id)
            if existing:
                # 更新
                existing.title = feed.title
                existing.url = feed.url
                existing.site_url = feed.site_url
                existing.icon_url = feed.icon_url
                existing.category = feed.category
                existing.updated_at = datetime.utcnow()
            else:
                # 新增
                self.session.add(feed)
                count += 1

        await self.session.commit()
        return count

    async def sync_articles(self, max_count: int = 100) -> SyncStatus:
        """同步未读文章，返回同步状态."""
        sync_status = SyncStatus(
            sync_type="incremental",
            status="running",
            started_at=datetime.utcnow(),
        )
        self.session.add(sync_status)
        await self.session.commit()

        try:
            articles = await self.freshrss.get_unread_items(count=max_count)
            fetched_count = 0

            for article in articles:
                # 检查是否已存在
                existing = await self.session.get(Article, article.id)
                if existing:
                    continue

                # 提取纯文本
                article.content_text = html_to_text(article.content or "")

                # 暂时跳过全文抓取（避免卡住）
                # TODO: 改为后台异步抓取
                article.fetch_status = "skipped"

                self.session.add(article)
                fetched_count += 1

            await self.session.commit()

            # 更新同步状态
            sync_status.status = "success"
            sync_status.articles_fetched = fetched_count
            sync_status.completed_at = datetime.utcnow()

        except Exception as e:
            sync_status.status = "failed"
            sync_status.error_message = str(e)
            sync_status.completed_at = datetime.utcnow()

        await self.session.commit()
        return sync_status

    async def _should_fetch_full_text(
        self,
        article: Article,
        feed: Feed | None,
    ) -> bool:
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

    async def get_latest_sync_status(self) -> SyncStatus | None:
        """获取最近一次同步状态."""
        stmt = select(SyncStatus).order_by(SyncStatus.started_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
