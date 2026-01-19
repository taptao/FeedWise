"""FeedWise 主应用入口."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from feedwise.api import analysis, articles, feeds, fetch, process, settings, sync
from feedwise.config import get_settings, set_dynamic_settings
from feedwise.models.database import init_db
from feedwise.scheduler import create_scheduler, shutdown_scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _load_dynamic_settings() -> None:
    """从数据库加载动态配置."""
    from feedwise.models.app_settings import AppSettings
    from feedwise.models.database import async_session_maker
    from sqlmodel import select

    session_factory = async_session_maker()
    async with session_factory() as session:
        result = await session.execute(select(AppSettings))
        db_settings = result.scalar_one_or_none()
        if db_settings:
            settings_dict = {
                "llm_provider": db_settings.llm_provider,
                "openai_api_key": db_settings.openai_api_key,
                "openai_base_url": db_settings.openai_base_url,
                "openai_model": db_settings.openai_model,
                "ollama_host": db_settings.ollama_host,
                "ollama_model": db_settings.ollama_model,
                "freshrss_url": db_settings.freshrss_url,
                "freshrss_username": db_settings.freshrss_username,
                "freshrss_api_password": db_settings.freshrss_api_password,
                "sync_interval_minutes": db_settings.sync_interval_minutes,
                "analysis_concurrency": db_settings.analysis_concurrency,
                "analysis_prompt_criteria": db_settings.analysis_prompt_criteria,
            }
            set_dynamic_settings(settings_dict)
            logger.info("动态配置已加载")


async def _reset_stuck_states() -> None:
    """重置卡住的中间状态（服务重启后恢复）."""
    from feedwise.models.database import async_session_maker
    from sqlalchemy import text

    session_factory = async_session_maker()
    async with session_factory() as session:
        # 重置 analyzing -> pending_analysis
        result = await session.execute(
            text("UPDATE articles SET process_status='pending_analysis' WHERE process_status='analyzing'")
        )
        analyzing_count = result.rowcount

        # 重置 fetching -> pending_fetch
        result = await session.execute(
            text("UPDATE articles SET process_status='pending_fetch' WHERE process_status='fetching'")
        )
        fetching_count = result.rowcount

        await session.commit()

        if analyzing_count > 0 or fetching_count > 0:
            logger.info(f"已重置卡住的状态: analyzing={analyzing_count}, fetching={fetching_count}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理."""
    app_settings = get_settings()

    # 启动时初始化
    logger.info("正在初始化数据库...")
    await init_db(app_settings.database_url)

    # 加载动态配置
    logger.info("正在加载动态配置...")
    await _load_dynamic_settings()

    # 重置卡住的中间状态
    logger.info("正在检查并重置卡住的状态...")
    await _reset_stuck_states()

    logger.info("正在启动定时任务...")
    create_scheduler(app_settings)

    logger.info("FeedWise 启动完成！")
    yield

    # 关闭时清理
    logger.info("正在关闭...")
    await shutdown_scheduler()
    logger.info("FeedWise 已关闭")


app = FastAPI(
    title="FeedWise",
    description="智能 RSS 阅读助手 - FreshRSS 内容分析与价值排序",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(articles.router)
app.include_router(feeds.router)
app.include_router(analysis.router)
app.include_router(fetch.router)
app.include_router(process.router)
app.include_router(sync.router)
app.include_router(settings.router)


@app.get("/")
async def root() -> dict:
    """根路径."""
    return {
        "name": "FeedWise",
        "version": "0.1.0",
        "description": "智能 RSS 阅读助手",
    }


@app.get("/health")
async def health() -> dict:
    """健康检查."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "feedwise.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
