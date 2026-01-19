"""测试配置和 fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from feedwise.main import app
from feedwise.models.article import Article
from feedwise.models.feed import Feed


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """创建测试用的 HTTP 客户端."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试用的内存数据库会话."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_feed(async_session: AsyncSession) -> Feed:
    """创建测试用的 Feed."""
    feed = Feed(
        id="feed-001",
        title="Test Feed",
        url="https://example.com/feed.xml",
        site_url="https://example.com",
        fetch_full_text="auto",
    )
    async_session.add(feed)
    await async_session.commit()
    await async_session.refresh(feed)
    return feed


@pytest_asyncio.fixture
async def sample_articles(
    async_session: AsyncSession, sample_feed: Feed
) -> list[Article]:
    """创建测试用的文章列表."""
    articles = [
        Article(
            id="article-001",
            feed_id=sample_feed.id,
            title="Article 1",
            url="https://example.com/article-1",
            content_text="Short content",
            process_status="synced",
        ),
        Article(
            id="article-002",
            feed_id=sample_feed.id,
            title="Article 2",
            url="https://example.com/article-2",
            content_text="Another short content",
            process_status="pending_fetch",
        ),
        Article(
            id="article-003",
            feed_id=sample_feed.id,
            title="Article 3",
            url="https://example.com/article-3",
            content_text="Content for analysis",
            process_status="pending_analysis",
            full_content="Full content here for analysis",
        ),
        Article(
            id="article-004",
            feed_id=sample_feed.id,
            title="Article 4 - Failed",
            url="https://example.com/article-4",
            content_text="Failed content",
            process_status="failed",
            process_stage="fetch",
            process_error="Connection timeout",
        ),
        Article(
            id="article-005",
            feed_id=sample_feed.id,
            title="Article 5 - Done",
            url="https://example.com/article-5",
            content_text="Done content",
            process_status="done",
            full_content="Full content",
        ),
    ]
    for article in articles:
        async_session.add(article)
    await async_session.commit()
    return articles
