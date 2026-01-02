"""文章排序服务."""

from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from feedwise.models.analysis import ArticleAnalysis
from feedwise.models.article import Article
from feedwise.models.feed import Feed


class ArticleRanker:
    """文章排序器."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_ranked_articles(
        self,
        sort_by: Literal["value", "date", "feed"] = "value",
        filter_by: Literal["unread", "starred", "all"] = "unread",
        feed_id: str | None = None,
        min_score: float | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[dict], int]:
        """
        获取排序后的文章列表.

        返回：(文章列表, 总数)
        """
        # 构建基础查询
        stmt = (
            select(Article, ArticleAnalysis, Feed)
            .outerjoin(
                ArticleAnalysis,
                Article.id == ArticleAnalysis.article_id,
            )
            .outerjoin(
                Feed,
                Article.feed_id == Feed.id,
            )
        )

        # 应用筛选条件
        if filter_by == "unread":
            stmt = stmt.where(Article.is_read == False)  # noqa: E712
        elif filter_by == "starred":
            stmt = stmt.where(Article.is_starred == True)  # noqa: E712

        if feed_id:
            stmt = stmt.where(Article.feed_id == feed_id)

        if min_score is not None:
            stmt = stmt.where(ArticleAnalysis.value_score >= min_score)

        # 计算总数
        count_stmt = select(Article.id).outerjoin(
            ArticleAnalysis,
            Article.id == ArticleAnalysis.article_id,
        )
        if filter_by == "unread":
            count_stmt = count_stmt.where(Article.is_read == False)  # noqa: E712
        elif filter_by == "starred":
            count_stmt = count_stmt.where(Article.is_starred == True)  # noqa: E712
        if feed_id:
            count_stmt = count_stmt.where(Article.feed_id == feed_id)
        if min_score is not None:
            count_stmt = count_stmt.where(ArticleAnalysis.value_score >= min_score)

        count_result = await self.session.execute(count_stmt)
        total = len(count_result.all())

        # 应用排序
        if sort_by == "value":
            # 按价值分排序，无分数的放最后
            stmt = stmt.order_by(
                ArticleAnalysis.value_score.desc().nulls_last(),
                Article.published_at.desc().nulls_last(),
            )
        elif sort_by == "date":
            stmt = stmt.order_by(Article.published_at.desc().nulls_last())
        else:  # feed
            stmt = stmt.order_by(
                Feed.title.asc().nulls_last(),
                Article.published_at.desc().nulls_last(),
            )

        # 分页
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        # 执行查询
        result = await self.session.execute(stmt)
        rows = result.all()

        # 构建返回数据
        articles: list[dict] = []
        for article, analysis, feed in rows:
            articles.append(self._build_article_response(article, analysis, feed))

        return articles, total

    def _build_article_response(
        self,
        article: Article,
        analysis: ArticleAnalysis | None,
        feed: Feed | None,
    ) -> dict:
        """构建文章响应数据."""
        import json

        response = {
            "id": article.id,
            "title": article.title,
            "author": article.author,
            "url": article.url,
            "published_at": (
                article.published_at.isoformat() if article.published_at else None
            ),
            "is_read": article.is_read,
            "is_starred": article.is_starred,
            "content_source": article.content_source,
            "fetch_status": article.fetch_status,
            "feed": None,
            "analysis": None,
        }

        if feed:
            response["feed"] = {
                "id": feed.id,
                "title": feed.title,
                "icon_url": feed.icon_url,
                "category": feed.category,
            }

        if analysis:
            response["analysis"] = {
                "summary": analysis.summary,
                "value_score": analysis.value_score,
                "reading_time": analysis.reading_time,
                "language": analysis.language,
                "tags": json.loads(analysis.tags) if analysis.tags else [],
                "key_points": json.loads(analysis.key_points)
                if analysis.key_points
                else [],
            }

        return response

    def calculate_composite_score(
        self,
        value_score: float | None,
        published_at: datetime | None,
        feed_priority: int = 5,
    ) -> float:
        """
        计算综合评分.

        综合考虑：AI 价值评分、时效性、Feed 优先级
        """
        score = 0.0

        # AI 价值评分权重 60%
        if value_score is not None:
            score += value_score * 0.6

        # 时效性权重 25%（24小时内满分）
        if published_at:
            hours_ago = (datetime.utcnow() - published_at).total_seconds() / 3600
            freshness = max(0, 10 - hours_ago / 2.4)  # 24小时后为0
            score += freshness * 0.25

        # Feed 优先级权重 15%
        score += feed_priority * 0.15

        return round(score, 2)

