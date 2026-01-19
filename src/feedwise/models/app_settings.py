"""应用动态配置模型."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class AppSettings(SQLModel, table=True):
    """应用动态配置表（单行存储）."""

    __tablename__ = "app_settings"

    id: int = Field(default=1, primary_key=True)

    # LLM 配置
    llm_provider: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    openai_base_url: str | None = Field(default=None)
    openai_model: str | None = Field(default=None)
    ollama_host: str | None = Field(default=None)
    ollama_model: str | None = Field(default=None)

    # FreshRSS 配置
    freshrss_url: str | None = Field(default=None)
    freshrss_username: str | None = Field(default=None)
    freshrss_api_password: str | None = Field(default=None)

    # 应用配置
    sync_interval_minutes: int | None = Field(default=None)
    analysis_concurrency: int | None = Field(default=None)  # AI 分析并发数
    analysis_prompt_criteria: str | None = Field(default=None)  # 自定义评分标准

    updated_at: datetime = Field(default_factory=datetime.utcnow)
