"""文章 API."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from feedwise.core.ranking import ArticleRanker
from feedwise.models.analysis import ArticleAnalysis
from feedwise.models.article import Article
from feedwise.models.database import get_session

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("")
async def list_articles(
    sort: Literal["value", "date", "feed"] = Query("value", description="排序方式"),
    filter: Literal["unread", "starred", "all"] = Query(
        "unread", description="筛选条件"
    ),
    feed_id: str | None = Query(None, description="按 Feed 筛选"),
    min_score: float | None = Query(None, ge=0, le=10, description="最低价值分"),
    tag: str | None = Query(None, description="按标签筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取文章列表."""
    ranker = ArticleRanker(session)
    articles, total = await ranker.get_ranked_articles(
        sort_by=sort,
        filter_by=filter,
        feed_id=feed_id,
        min_score=min_score,
        tag=tag,
        page=page,
        limit=limit,
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": articles,
    }


@router.get("/tags")
async def get_all_tags(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取所有可用的标签及其数量."""
    stmt = select(ArticleAnalysis.tags).where(ArticleAnalysis.tags.isnot(None))
    result = await session.execute(stmt)
    rows = result.scalars().all()

    # 统计标签出现次数
    tag_counts: dict[str, int] = {}
    for tags_json in rows:
        if tags_json:
            try:
                tags = json.loads(tags_json)
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except json.JSONDecodeError:
                pass

    # 按数量排序
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "tags": [{"name": name, "count": count} for name, count in sorted_tags],
    }


@router.get("/detail")
async def get_article(
    article_id: str = Query(..., description="文章 ID"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取文章详情（article_id 作为 query 参数）."""
    article = await session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    return {
        "id": article.id,
        "feed_id": article.feed_id,
        "title": article.title,
        "author": article.author,
        "url": article.url,
        # 分别返回，让前端能明确区分
        "content": article.full_content or article.content_text or article.content,
        "full_content": article.full_content,  # 抓取到的全文（可能为 None）
        "content_html": article.content,  # RSS 原始 HTML（通常是摘要）
        "published_at": article.published_at.isoformat()
        if article.published_at
        else None,
        "is_read": article.is_read,
        "is_starred": article.is_starred,
        "user_rating": article.user_rating,
        "content_source": article.content_source,
        "fetch_status": article.fetch_status,
    }


@router.patch("/read")
async def mark_read(
    article_id: str = Query(..., description="文章 ID"),
    read: bool = Query(True, description="是否已读"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """标记文章已读/未读."""
    article = await session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    article.is_read = read
    await session.commit()

    return {"id": article_id, "is_read": read}


@router.patch("/star")
async def toggle_star(
    article_id: str = Query(..., description="文章 ID"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """切换收藏状态."""
    article = await session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    article.is_starred = not article.is_starred
    await session.commit()

    return {"id": article_id, "is_starred": article.is_starred}


@router.post("/fetch-full")
async def fetch_full_content(
    article_id: str = Query(..., description="文章 ID"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """手动触发全文抓取."""
    from feedwise.fetcher.extractor import FullTextExtractor

    article = await session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    if not article.url:
        raise HTTPException(status_code=400, detail="文章没有原文链接")

    extractor = FullTextExtractor()
    result = await extractor.fetch(article.url)

    if result.success and result.content:
        article.full_content = result.content
        article.content_source = "fetched"
        article.fetch_status = "success"
        await session.commit()
        return {
            "success": True,
            "content": result.content,
            "word_count": result.word_count,
        }

    article.fetch_status = "failed"
    await session.commit()
    return {
        "success": False,
        "error": result.error,
    }


@router.post("/rate")
async def rate_article(
    article_id: str = Query(..., description="文章 ID"),
    rating: int = Query(..., ge=-1, le=1, description="评价: 1=喜欢, -1=不喜欢, 0=取消"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """给文章评价（喜欢/不喜欢）."""
    from feedwise.models.feed import Feed

    article = await session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    old_rating = article.user_rating
    new_rating = rating if rating != 0 else None

    # 更新文章评价
    article.user_rating = new_rating
    
    # 更新 Feed 统计
    feed = await session.get(Feed, article.feed_id)
    if feed:
        # 撤销旧评价
        if old_rating == 1:
            feed.likes_count = max(0, feed.likes_count - 1)
        elif old_rating == -1:
            feed.dislikes_count = max(0, feed.dislikes_count - 1)
        
        # 应用新评价
        if new_rating == 1:
            feed.likes_count += 1
        elif new_rating == -1:
            feed.dislikes_count += 1

    await session.commit()

    return {
        "id": article_id,
        "user_rating": article.user_rating,
        "feed_likes": feed.likes_count if feed else 0,
        "feed_dislikes": feed.dislikes_count if feed else 0,
    }
