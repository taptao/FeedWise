"""Article 文章模型."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Article(SQLModel, table=True):
    """RSS 文章."""

    __tablename__ = "articles"  # type: ignore[assignment]

    id: str = Field(primary_key=True, description="FreshRSS 中的 article ID")
    feed_id: str = Field(foreign_key="feeds.id", description="关联 Feed")
    title: str = Field(description="标题")
    author: str | None = Field(default=None, description="作者")
    url: str | None = Field(default=None, description="原文链接")
    content: str | None = Field(default=None, description="HTML 内容")
    content_text: str | None = Field(default=None, description="纯文本内容")
    full_content: str | None = Field(default=None, description="抓取的全文内容")
    content_source: str = Field(default="feed", description="内容来源: feed|fetched")
    fetch_status: str | None = Field(
        default=None,
        description="全文抓取状态: pending|success|failed|skipped (deprecated)",
    )
    process_status: str = Field(
        default="synced",
        description="处理状态: synced|pending_fetch|fetching|pending_analysis|analyzing|done|failed",
    )
    process_error: str | None = Field(default=None, description="处理错误信息")
    process_stage: str | None = Field(
        default=None, description="失败阶段: fetch|analysis"
    )
    published_at: datetime | None = Field(default=None, description="发布时间")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow, description="抓取时间"
    )
    is_read: bool = Field(default=False, description="是否已读")
    is_starred: bool = Field(default=False, description="是否收藏")
