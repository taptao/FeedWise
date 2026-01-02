"""全文抓取 API."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from feedwise.config import get_settings
from feedwise.core.fetch_runner import (
    FetchTaskRunner,
    get_batch_status,
    get_current_batch_id,
    get_latest_batch_status,
)
from feedwise.models.database import async_session_maker, get_session

router = APIRouter(prefix="/api/fetch", tags=["fetch"])


@router.get("/stats")
async def get_fetch_stats(
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """获取抓取状态统计."""
    runner = FetchTaskRunner(session)
    return await runner.get_stats()


@router.get("/progress")
async def get_fetch_progress() -> dict:
    """获取当前抓取进度."""
    current_id = get_current_batch_id()

    if current_id:
        status = get_batch_status(current_id)
        if status:
            return {
                "batch_id": status.batch_id,
                "status": status.status,
                "total": status.total,
                "completed": status.completed,
                "failed": status.failed,
                "skipped": status.skipped,
                "started_at": status.started_at.isoformat(),
                "current_item": status.current_article,
            }

    # 无任务运行时，返回最近批次信息
    latest = get_latest_batch_status()
    if latest:
        return {
            "status": "idle",
            "last_batch_id": latest.batch_id,
            "last_completed_at": (
                latest.completed_at.isoformat() if latest.completed_at else None
            ),
            "last_result": {
                "total": latest.total,
                "completed": latest.completed,
                "failed": latest.failed,
                "skipped": latest.skipped,
            },
        }

    return {"status": "idle"}


@router.get("/failed")
async def get_failed_articles(
    page: int = 1,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取抓取失败的文章列表."""
    runner = FetchTaskRunner(session)
    items, total = await runner.get_failed_articles(page, limit)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items,
    }


@router.post("/batch")
async def trigger_batch_fetch(
    limit: int = 20,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """触发批量抓取."""
    # 检查是否已有任务在运行
    if get_current_batch_id():
        raise HTTPException(status_code=409, detail="已有抓取任务在运行中")

    # 检查是否有待抓取文章
    runner = FetchTaskRunner(session)
    pending_count = await runner.get_pending_count()

    if pending_count == 0:
        return {"message": "没有待抓取的文章", "count": 0}

    # 获取配置
    settings = get_settings()
    actual_limit = min(limit, pending_count, settings.fetch_batch_size)

    # 后台执行
    background_tasks.add_task(
        _run_batch_fetch,
        actual_limit,
        settings.fetch_concurrency,
    )

    return {
        "batch_id": f"fetch_{int(__import__('time').time())}",
        "message": f"开始抓取 {actual_limit} 篇文章",
        "count": actual_limit,
    }


@router.post("/retry")
async def retry_failed(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """重试失败的文章."""
    # 检查是否已有任务在运行
    if get_current_batch_id():
        raise HTTPException(status_code=409, detail="已有抓取任务在运行中")

    # 重置失败状态
    runner = FetchTaskRunner(session)
    reset_count = await runner.reset_failed_to_pending()

    if reset_count == 0:
        return {"message": "没有失败的文章需要重试", "reset_count": 0}

    # 获取配置并触发抓取
    settings = get_settings()

    background_tasks.add_task(
        _run_batch_fetch,
        min(reset_count, settings.fetch_batch_size),
        settings.fetch_concurrency,
    )

    return {
        "reset_count": reset_count,
        "message": f"已重置 {reset_count} 篇文章，开始重新抓取",
    }


async def _run_batch_fetch(batch_size: int, concurrency: int) -> None:
    """后台执行批量抓取."""
    async with async_session_maker()() as session:
        runner = FetchTaskRunner(session)
        await runner.run_batch(batch_size=batch_size, concurrency=concurrency)
