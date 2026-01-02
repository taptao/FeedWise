"""设置 API."""

from fastapi import APIRouter
from pydantic import BaseModel

from feedwise.config import get_settings
from feedwise.core.freshrss import FreshRSSClient, FreshRSSConfig
from feedwise.llm import create_llm_provider
from feedwise.llm.base import Message

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


@router.get("")
async def get_current_settings() -> SettingsResponse:
    """获取当前设置."""
    settings = get_settings()

    freshrss_configured = bool(
        settings.freshrss_url
        and settings.freshrss_username
        and settings.freshrss_api_password
    )

    llm_configured = bool(
        (settings.llm_provider == "openai" and settings.openai_api_key)
        or (settings.llm_provider == "ollama" and settings.ollama_host)
    )

    return SettingsResponse(
        freshrss_url=settings.freshrss_url,
        freshrss_username=settings.freshrss_username,
        freshrss_configured=freshrss_configured,
        llm_provider=settings.llm_provider,
        openai_base_url=settings.openai_base_url,
        openai_model=settings.openai_model,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_model,
        llm_configured=llm_configured,
        sync_interval_minutes=settings.sync_interval_minutes,
    )


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
async def test_llm_connection() -> TestConnectionResult:
    """测试 LLM 连接."""
    settings = get_settings()

    try:
        provider = create_llm_provider(settings)
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

