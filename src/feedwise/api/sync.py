"""同步 API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from feedwise.config import get_settings
from feedwise.core.freshrss import FreshRSSClient, FreshRSSConfig
from feedwise.core.sync import SyncService
from feedwise.models.database import get_session

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("")
async def trigger_sync(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """触发同步."""
    settings = get_settings()

    if not settings.freshrss_url:
        raise HTTPException(status_code=400, detail="FreshRSS 未配置")

    config = FreshRSSConfig(
        base_url=settings.freshrss_url,
        username=settings.freshrss_username,
        api_password=settings.freshrss_api_password,
    )

    client = FreshRSSClient(config)
    try:
        await client.authenticate()

        sync_service = SyncService(client, session)

        # 同步 Feeds
        feeds_count = await sync_service.sync_feeds()

        # 同步文章
        sync_status = await sync_service.sync_articles()

        return {
            "success": sync_status.status == "success",
            "feeds_synced": feeds_count,
            "articles_fetched": sync_status.articles_fetched,
            "status": sync_status.status,
            "error": sync_status.error_message,
        }
    finally:
        await client.close()


@router.get("/status")
async def get_sync_status(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取最近同步状态."""
    from sqlmodel import select

    from feedwise.models.sync import SyncStatus

    stmt = select(SyncStatus).order_by(SyncStatus.started_at.desc()).limit(5)
    result = await session.execute(stmt)
    statuses = result.scalars().all()

    return {
        "items": [
            {
                "id": s.id,
                "sync_type": s.sync_type,
                "status": s.status,
                "articles_fetched": s.articles_fetched,
                "articles_analyzed": s.articles_analyzed,
                "error_message": s.error_message,
                "started_at": s.started_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in statuses
        ]
    }
