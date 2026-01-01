"""文章 API."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from feedwise.core.ranking import ArticleRanker
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
        page=page,
        limit=limit,
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": articles,
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

    # 获取用于展示的内容（优先使用全文）
    content = article.full_content or article.content_text or article.content

    return {
        "id": article.id,
        "feed_id": article.feed_id,
        "title": article.title,
        "author": article.author,
        "url": article.url,
        "content": content,
        "content_html": article.content,
        "published_at": article.published_at.isoformat()
        if article.published_at
        else None,
        "is_read": article.is_read,
        "is_starred": article.is_starred,
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
