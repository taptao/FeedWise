"""FeedWise 主应用入口."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from feedwise.api import analysis, articles, feeds, fetch, process, settings, sync
from feedwise.config import get_settings
from feedwise.models.database import init_db
from feedwise.scheduler import create_scheduler, shutdown_scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理."""
    app_settings = get_settings()

    # 启动时初始化
    logger.info("正在初始化数据库...")
    await init_db(app_settings.database_url)

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
