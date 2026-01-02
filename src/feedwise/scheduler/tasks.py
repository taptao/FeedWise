"""定时任务定义."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from feedwise.config import Settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def sync_task(settings: Settings) -> None:
    """同步任务：从 FreshRSS 拉取最新文章."""
    from feedwise.core.freshrss import FreshRSSClient, FreshRSSConfig
    from feedwise.core.sync import SyncService
    from feedwise.models.database import get_session

    if not settings.freshrss_url:
        logger.warning("FreshRSS 未配置，跳过同步")
        return

    logger.info("开始同步任务...")

    config = FreshRSSConfig(
        base_url=settings.freshrss_url,
        username=settings.freshrss_username,
        api_password=settings.freshrss_api_password,
    )

    client = FreshRSSClient(config)
    try:
        await client.authenticate()

        # 获取数据库会话
        async for session in get_session():
            sync_service = SyncService(client, session)

            # 同步 Feeds
            feeds_count = await sync_service.sync_feeds()
            logger.info(f"同步了 {feeds_count} 个 Feed")

            # 同步文章
            sync_status = await sync_service.sync_articles()
            logger.info(
                f"同步完成: 状态={sync_status.status}, "
                f"文章数={sync_status.articles_fetched}"
            )
            break  # 只需要一个会话

    except Exception as e:
        logger.exception(f"同步任务失败: {e}")
    finally:
        await client.close()


def create_scheduler(settings: Settings) -> AsyncIOScheduler:
    """创建并启动定时任务调度器."""
    global _scheduler

    _scheduler = AsyncIOScheduler()

    # 添加同步任务
    _scheduler.add_job(
        sync_task,
        "interval",
        minutes=settings.sync_interval_minutes,
        args=[settings],
        id="sync_task",
        name="FreshRSS 同步任务",
        replace_existing=True,
    )

    # 启动时立即执行一次
    _scheduler.add_job(
        sync_task,
        "date",  # 一次性任务
        args=[settings],
        id="sync_task_initial",
        name="初始同步",
    )

    _scheduler.start()
    logger.info(
        f"定时任务调度器已启动，同步间隔: {settings.sync_interval_minutes} 分钟"
    )

    return _scheduler


async def shutdown_scheduler() -> None:
    """关闭定时任务调度器."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("定时任务调度器已关闭")
        _scheduler = None

