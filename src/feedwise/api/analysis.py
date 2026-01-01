"""分析 API."""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from feedwise.config import get_settings
from feedwise.llm import ArticleAnalyzer, create_llm_provider
from feedwise.models.analysis import ArticleAnalysis
from feedwise.models.article import Article
from feedwise.models.database import async_session_maker, get_session

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# 批量分析状态
_batch_status: dict[str, dict] = {}


@router.get("/article")
async def get_analysis(
    article_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取文章分析结果（article_id 作为 query 参数）."""
    from sqlmodel import select

    stmt = select(ArticleAnalysis).where(ArticleAnalysis.article_id == article_id)
    result = await session.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="分析结果不存在")

    return {
        "article_id": analysis.article_id,
        "summary": analysis.summary,
        "key_points": json.loads(analysis.key_points) if analysis.key_points else [],
        "value_score": analysis.value_score,
        "reading_time": analysis.reading_time,
        "language": analysis.language,
        "tags": json.loads(analysis.tags) if analysis.tags else [],
        "model_used": analysis.model_used,
        "analyzed_at": analysis.analyzed_at.isoformat(),
    }


@router.post("/article")
async def trigger_analysis(
    article_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """触发文章分析（article_id 作为 query 参数）."""
    article = await session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 获取用于分析的内容
    content = article.full_content or article.content_text or ""
    if not content:
        raise HTTPException(status_code=400, detail="文章没有可分析的内容")

    # 创建 LLM Provider
    settings = get_settings()
    provider = create_llm_provider(settings)
    analyzer = ArticleAnalyzer(provider)

    # 执行分析
    result = await analyzer.analyze(
        title=article.title,
        content=content,
        feed_name="",  # TODO: 获取 feed 名称
    )

    # 检查是否已有分析结果
    from sqlmodel import select

    stmt = select(ArticleAnalysis).where(ArticleAnalysis.article_id == article_id)
    existing_result = await session.execute(stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        # 更新
        existing.summary = result.summary
        existing.key_points = json.dumps(result.key_points, ensure_ascii=False)
        existing.value_score = result.value_score
        existing.reading_time = result.reading_time
        existing.language = result.language
        existing.tags = json.dumps(result.tags, ensure_ascii=False)
        existing.model_used = (
            settings.openai_model
            if settings.llm_provider == "openai"
            else settings.ollama_model
        )
    else:
        # 新增
        analysis = ArticleAnalysis(
            article_id=article_id,
            summary=result.summary,
            key_points=json.dumps(result.key_points, ensure_ascii=False),
            value_score=result.value_score,
            reading_time=result.reading_time,
            language=result.language,
            tags=json.dumps(result.tags, ensure_ascii=False),
            model_used=(
                settings.openai_model
                if settings.llm_provider == "openai"
                else settings.ollama_model
            ),
        )
        session.add(analysis)

    await session.commit()

    return {
        "article_id": article_id,
        "summary": result.summary,
        "key_points": result.key_points,
        "value_score": result.value_score,
        "reading_time": result.reading_time,
        "language": result.language,
        "tags": result.tags,
    }


@router.post("/batch")
async def trigger_batch_analysis(
    limit: int = 20,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """批量分析未分析的文章（后台执行）."""
    # 查找未分析的文章
    subquery = select(ArticleAnalysis.article_id)
    stmt = (
        select(Article)
        .where(Article.id.notin_(subquery))
        .where(Article.content_text.isnot(None))
        .where(Article.content_text != "")
        .limit(limit)
    )
    result = await session.execute(stmt)
    articles = result.scalars().all()

    if not articles:
        return {"message": "没有需要分析的文章", "count": 0}

    article_ids = [a.id for a in articles]
    batch_id = f"batch_{int(asyncio.get_event_loop().time())}"

    _batch_status[batch_id] = {
        "total": len(article_ids),
        "completed": 0,
        "failed": 0,
        "status": "running",
    }

    # 后台执行批量分析
    background_tasks.add_task(_run_batch_analysis, batch_id, article_ids)

    return {
        "batch_id": batch_id,
        "message": f"开始分析 {len(article_ids)} 篇文章",
        "count": len(article_ids),
    }


@router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str) -> dict:
    """获取批量分析状态."""
    if batch_id not in _batch_status:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    return _batch_status[batch_id]


async def _run_batch_analysis(batch_id: str, article_ids: list[str]) -> None:
    """后台执行批量分析."""
    settings = get_settings()
    provider = create_llm_provider(settings)
    analyzer = ArticleAnalyzer(provider)
    model_name = (
        settings.openai_model
        if settings.llm_provider == "openai"
        else settings.ollama_model
    )

    async with async_session_maker()() as session:
        for article_id in article_ids:
            try:
                article = await session.get(Article, article_id)
                if not article:
                    _batch_status[batch_id]["failed"] += 1
                    continue

                content = article.full_content or article.content_text or ""
                if not content:
                    _batch_status[batch_id]["failed"] += 1
                    continue

                # 执行分析
                result = await analyzer.analyze(
                    title=article.title,
                    content=content,
                    feed_name="",
                )

                # 保存结果
                analysis = ArticleAnalysis(
                    article_id=article_id,
                    summary=result.summary,
                    key_points=json.dumps(result.key_points, ensure_ascii=False),
                    value_score=result.value_score,
                    reading_time=result.reading_time,
                    language=result.language,
                    tags=json.dumps(result.tags, ensure_ascii=False),
                    model_used=model_name,
                )
                session.add(analysis)
                await session.commit()

                _batch_status[batch_id]["completed"] += 1

            except Exception:
                _batch_status[batch_id]["failed"] += 1

    _batch_status[batch_id]["status"] = "completed"


@router.get("/stream/{article_id}")
async def stream_analysis(
    article_id: str,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """流式返回分析结果（SSE）."""
    article = await session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    content = article.full_content or article.content_text or ""
    if not content:
        raise HTTPException(status_code=400, detail="文章没有可分析的内容")

    async def generate() -> AsyncIterator[str]:
        settings = get_settings()
        provider = create_llm_provider(settings)
        analyzer = ArticleAnalyzer(provider)

        yield f"event: start\ndata: {json.dumps({'status': 'analyzing'})}\n\n"

        full_response = ""
        async for chunk in analyzer.analyze_stream(
            title=article.title,
            content=content,
            feed_name="",
        ):
            full_response += chunk
            yield f"event: chunk\ndata: {json.dumps({'chunk': chunk})}\n\n"

        yield f"event: done\ndata: {json.dumps({'status': 'completed', 'response': full_response})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
