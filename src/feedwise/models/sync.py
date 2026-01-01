"""SyncStatus 同步状态模型."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class SyncStatus(SQLModel, table=True):
    """同步任务状态."""

    __tablename__ = "sync_status"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    sync_type: str = Field(description="同步类型: full|incremental")
    status: str = Field(description="状态: running|success|failed")
    articles_fetched: int = Field(default=0, description="抓取文章数")
    articles_analyzed: int = Field(default=0, description="分析文章数")
    error_message: str | None = Field(default=None, description="错误信息")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = Field(default=None)
