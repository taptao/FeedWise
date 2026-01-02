"""Feed 订阅源模型."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Feed(SQLModel, table=True):
    """RSS 订阅源."""

    __tablename__ = "feeds"  # type: ignore[assignment]

    id: str = Field(primary_key=True, description="FreshRSS 中的 feed ID (streamId)")
    title: str = Field(description="Feed 标题")
    url: str = Field(description="Feed URL")
    site_url: str | None = Field(default=None, description="网站 URL")
    icon_url: str | None = Field(default=None, description="图标 URL")
    category: str | None = Field(default=None, description="分类")
    fetch_full_text: str = Field(
        default="auto", description="全文抓取策略: auto|always|never"
    )
    priority: int = Field(default=5, ge=1, le=10, description="用户自定义优先级")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
