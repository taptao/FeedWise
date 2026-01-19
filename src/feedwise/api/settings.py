"""设置 API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from feedwise.config import (
    get_effective_setting,
    get_settings,
    set_dynamic_settings,
)
from feedwise.core.freshrss import FreshRSSClient, FreshRSSConfig
from feedwise.llm import create_llm_provider
from feedwise.llm.base import Message
from feedwise.models.app_settings import AppSettings
from feedwise.models.database import get_session

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """设置响应."""

    # FreshRSS
    freshrss_url: str
    freshrss_username: str
    freshrss_configured: bool

    # LLM
    llm_provider: str
    openai_base_url: str
    openai_model: str
    ollama_host: str
    ollama_model: str
    llm_configured: bool

    # App
    sync_interval_minutes: int
    analysis_concurrency: int
    analysis_prompt_criteria: str | None


@router.get("")
async def get_current_settings(
    session: AsyncSession = Depends(get_session),
) -> SettingsResponse:
    """获取当前设置（动态配置优先）."""
    # 加载数据库配置到缓存
    await load_dynamic_settings(session)

    env_settings = get_settings()

    # 获取有效配置（动态优先）
    llm_provider = str(
        get_effective_setting("llm_provider") or env_settings.llm_provider
    )
    ollama_host = str(get_effective_setting("ollama_host") or env_settings.ollama_host)
    ollama_model = str(
        get_effective_setting("ollama_model") or env_settings.ollama_model
    )
    openai_base_url = str(
        get_effective_setting("openai_base_url") or env_settings.openai_base_url
    )
    openai_model = str(
        get_effective_setting("openai_model") or env_settings.openai_model
    )
    freshrss_url = str(
        get_effective_setting("freshrss_url") or env_settings.freshrss_url
    )
    freshrss_username = str(
        get_effective_setting("freshrss_username") or env_settings.freshrss_username
    )
    sync_interval = get_effective_setting("sync_interval_minutes")
    sync_interval_minutes = (
        int(sync_interval) if sync_interval else env_settings.sync_interval_minutes
    )
    analysis_concurrency_val = get_effective_setting("analysis_concurrency")
    analysis_concurrency = (
        int(analysis_concurrency_val) if analysis_concurrency_val else 1
    )
    analysis_prompt_criteria = get_effective_setting("analysis_prompt_criteria")

    freshrss_configured = bool(freshrss_url and freshrss_username)
    llm_configured = bool(
        (llm_provider == "openai" and env_settings.openai_api_key)
        or (llm_provider == "ollama" and ollama_host)
    )

    return SettingsResponse(
        freshrss_url=freshrss_url,
        freshrss_username=freshrss_username,
        freshrss_configured=freshrss_configured,
        llm_provider=llm_provider,
        openai_base_url=openai_base_url,
        openai_model=openai_model,
        ollama_host=ollama_host,
        ollama_model=ollama_model,
        llm_configured=llm_configured,
        sync_interval_minutes=sync_interval_minutes,
        analysis_concurrency=analysis_concurrency,
        analysis_prompt_criteria=str(analysis_prompt_criteria)
        if analysis_prompt_criteria
        else None,
    )


async def load_dynamic_settings(session: AsyncSession) -> None:
    """从数据库加载动态配置到缓存."""
    result = await session.execute(select(AppSettings).where(AppSettings.id == 1))
    db_settings = result.scalar_one_or_none()

    if db_settings:
        settings_dict: dict[str, str | int | None] = {
            "llm_provider": db_settings.llm_provider,
            "ollama_host": db_settings.ollama_host,
            "ollama_model": db_settings.ollama_model,
            "openai_base_url": db_settings.openai_base_url,
            "openai_model": db_settings.openai_model,
            "openai_api_key": db_settings.openai_api_key,
            "freshrss_url": db_settings.freshrss_url,
            "freshrss_username": db_settings.freshrss_username,
            "freshrss_api_password": db_settings.freshrss_api_password,
            "sync_interval_minutes": db_settings.sync_interval_minutes,
            "analysis_concurrency": db_settings.analysis_concurrency,
            "analysis_prompt_criteria": db_settings.analysis_prompt_criteria,
        }
        set_dynamic_settings(settings_dict)


class TestConnectionResult(BaseModel):
    """连接测试结果."""

    success: bool
    message: str


@router.post("/test-freshrss")
async def test_freshrss_connection() -> TestConnectionResult:
    """测试 FreshRSS 连接."""
    settings = get_settings()

    if not settings.freshrss_url:
        return TestConnectionResult(success=False, message="FreshRSS URL 未配置")

    config = FreshRSSConfig(
        base_url=settings.freshrss_url,
        username=settings.freshrss_username,
        api_password=settings.freshrss_api_password,
    )

    client = FreshRSSClient(config)
    try:
        await client.authenticate()
        subscriptions = await client.get_subscriptions()
        return TestConnectionResult(
            success=True,
            message=f"连接成功，发现 {len(subscriptions)} 个订阅",
        )
    except Exception as e:
        return TestConnectionResult(success=False, message=str(e))
    finally:
        await client.close()


@router.post("/test-llm")
async def test_llm_connection(
    session: AsyncSession = Depends(get_session),
) -> TestConnectionResult:
    """测试 LLM 连接（使用动态配置）."""
    # 先加载动态配置
    await load_dynamic_settings(session)

    env_settings = get_settings()

    # 获取有效配置
    llm_provider = str(
        get_effective_setting("llm_provider") or env_settings.llm_provider
    )
    ollama_host = str(get_effective_setting("ollama_host") or env_settings.ollama_host)
    ollama_model = str(
        get_effective_setting("ollama_model") or env_settings.ollama_model
    )

    try:
        if llm_provider == "ollama":
            from feedwise.llm.base import LLMConfig
            from feedwise.llm.ollama import OllamaProvider

            config = LLMConfig(model=ollama_model)
            provider = OllamaProvider(config=config, host=ollama_host)
        else:
            provider = create_llm_provider(env_settings)

        messages = [Message(role="user", content="Say 'OK' if you can hear me.")]
        response = await provider.chat(messages)

        if response:
            return TestConnectionResult(
                success=True,
                message=f"LLM 连接成功: {response[:50]}...",
            )
        return TestConnectionResult(success=False, message="LLM 返回空响应")
    except Exception as e:
        return TestConnectionResult(success=False, message=str(e))


class SettingsUpdateRequest(BaseModel):
    """设置更新请求."""

    llm_provider: str | None = None
    ollama_host: str | None = None
    ollama_model: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    openai_api_key: str | None = None
    freshrss_url: str | None = None
    freshrss_username: str | None = None
    freshrss_api_password: str | None = None
    sync_interval_minutes: int | None = None
    analysis_concurrency: int | None = None
    analysis_prompt_criteria: str | None = None


class SettingsUpdateResponse(BaseModel):
    """设置更新响应."""

    success: bool
    message: str


@router.put("")
async def update_settings(
    request: SettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> SettingsUpdateResponse:
    """更新设置（保存到数据库，立即生效）."""
    from datetime import datetime

    from feedwise.core.processor import reset_analysis_semaphore

    # 获取或创建配置记录
    result = await session.execute(select(AppSettings).where(AppSettings.id == 1))
    db_settings = result.scalar_one_or_none()

    if not db_settings:
        db_settings = AppSettings(id=1)
        session.add(db_settings)

    # 更新非空字段
    update_fields = request.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        if value is not None:
            setattr(db_settings, key, value)

    db_settings.updated_at = datetime.utcnow()
    await session.commit()

    # 重新加载到缓存
    await load_dynamic_settings(session)

    # 如果更新了并发配置，重置信号量
    if "analysis_concurrency" in update_fields:
        reset_analysis_semaphore()

    return SettingsUpdateResponse(success=True, message="设置已更新")
