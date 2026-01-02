"""ArticleAnalysis 分析结果模型."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class ArticleAnalysis(SQLModel, table=True):
    """文章 AI 分析结果."""

    __tablename__ = "article_analysis"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    article_id: str = Field(
        foreign_key="articles.id", unique=True, description="关联文章"
    )
    summary: str | None = Field(default=None, description="AI 生成摘要")
    key_points: str | None = Field(default=None, description="关键要点 (JSON 数组)")
    value_score: float | None = Field(default=None, ge=0, le=10, description="价值评分")
    reading_time: int | None = Field(
        default=None, ge=0, description="预估阅读时间（分钟）"
    )
    language: str | None = Field(default=None, description="检测语言 (zh/en)")
    tags: str | None = Field(default=None, description="AI 生成标签 (JSON 数组)")
    model_used: str | None = Field(default=None, description="使用的模型")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

