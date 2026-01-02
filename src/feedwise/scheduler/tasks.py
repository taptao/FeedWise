"""定时任务定义."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from feedwise.config import Settings

logger = logging.getLogger(__name__)


async def fetch_task(settings: Settings) -> None:
    """全文抓取任务：处理 pending 状态的文章."""
    from feedwise.core.fetch_runner import FetchTaskRunner, get_current_batch_id
    from feedwise.models.database import get_session

    if not settings.fetch_enabled:
        logger.info("全文抓取已禁用，跳过")
        return

    # 检查是否已有任务在运行
    if get_current_batch_id():
        logger.info("已有抓取任务在运行，跳过本次调度")
        return

    logger.info("开始全文抓取任务...")

    async for session in get_session():
        runner = FetchTaskRunner(session)

        # 检查是否有待抓取文章
        pending_count = await runner.get_pending_count()
        if pending_count == 0:
            logger.info("没有待抓取的文章")
            return

        # 执行批量抓取
        status = await runner.run_batch(
            batch_size=settings.fetch_batch_size,
            concurrency=settings.fetch_concurrency,
        )

        logger.info(
            f"全文抓取完成: 成功={status.completed}, "
            f"失败={status.failed}, 跳过={status.skipped}"
        )
        break  # 只需要一个会话


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


async def sync_and_fetch_task(settings: Settings) -> None:
    """同步并抓取任务：同步后自动触发全文抓取."""
    await sync_task(settings)
    # 同步完成后，等待一小段时间再开始抓取
    import asyncio

    await asyncio.sleep(2)
    await fetch_task(settings)


def create_scheduler(settings: Settings) -> AsyncIOScheduler:
    """创建并启动定时任务调度器."""
    global _scheduler

    _scheduler = AsyncIOScheduler()

    # 添加同步+抓取任务（同步后自动抓取）
    _scheduler.add_job(
        sync_and_fetch_task,
        "interval",
        minutes=settings.sync_interval_minutes,
        args=[settings],
        id="sync_fetch_task",
        name="FreshRSS 同步+全文抓取",
        replace_existing=True,
    )

    # 启动时立即执行一次同步+抓取
    _scheduler.add_job(
        sync_and_fetch_task,
        "date",  # 一次性任务
        args=[settings],
        id="sync_fetch_task_initial",
        name="初始同步+抓取",
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
