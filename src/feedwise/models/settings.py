"""Settings 配置存储模型."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class SettingItem(SQLModel, table=True):
    """配置项存储."""

    __tablename__ = "settings"  # type: ignore[assignment]

    key: str = Field(primary_key=True, description="配置键")
    value: str = Field(description="配置值")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

