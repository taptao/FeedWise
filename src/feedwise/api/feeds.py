"""Feed 订阅源 API."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from feedwise.models.database import get_session
from feedwise.models.feed import Feed

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


@router.get("")
async def list_feeds(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取订阅列表."""
    stmt = select(Feed).order_by(Feed.category.asc().nulls_last(), Feed.title.asc())
    result = await session.execute(stmt)
    feeds = result.scalars().all()

    # 按分类分组
    categories: dict[str, list[dict]] = {}
    for feed in feeds:
        category = feed.category or "未分类"
        if category not in categories:
            categories[category] = []
        categories[category].append(
            {
                "id": feed.id,
                "title": feed.title,
                "url": feed.url,
                "site_url": feed.site_url,
                "icon_url": feed.icon_url,
                "priority": feed.priority,
                "fetch_full_text": feed.fetch_full_text,
            }
        )

    return {
        "total": len(feeds),
        "categories": categories,
    }


@router.get("/{feed_id}")
async def get_feed(
    feed_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取 Feed 详情."""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed 不存在")

    return {
        "id": feed.id,
        "title": feed.title,
        "url": feed.url,
        "site_url": feed.site_url,
        "icon_url": feed.icon_url,
        "category": feed.category,
        "priority": feed.priority,
        "fetch_full_text": feed.fetch_full_text,
        "created_at": feed.created_at.isoformat(),
        "updated_at": feed.updated_at.isoformat(),
    }


@router.patch("/{feed_id}/priority")
async def set_priority(
    feed_id: str,
    priority: int = Query(..., ge=1, le=10, description="优先级 1-10"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """设置 Feed 优先级."""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed 不存在")

    feed.priority = priority
    await session.commit()

    return {"id": feed_id, "priority": priority}


@router.patch("/{feed_id}/fetch-mode")
async def set_fetch_mode(
    feed_id: str,
    mode: Literal["auto", "always", "never"] = Query(..., description="全文抓取模式"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """设置全文抓取模式."""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed 不存在")

    feed.fetch_full_text = mode
    await session.commit()

    return {"id": feed_id, "fetch_full_text": mode}

