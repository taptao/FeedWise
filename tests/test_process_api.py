"""测试 Process API 端点."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from feedwise.main import app
from feedwise.models.article import Article
from feedwise.models.database import get_session
from feedwise.models.feed import Feed


@pytest.fixture
async def test_engine():
    """创建测试数据库引擎."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session_factory(test_engine):
    """创建测试会话工厂."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def test_session(test_session_factory):
    """创建测试会话."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def setup_test_data(test_session: AsyncSession):
    """设置测试数据."""
    feed = Feed(
        id="feed-api-test",
        title="API Test Feed",
        url="https://example.com/feed.xml",
    )
    test_session.add(feed)

    articles = [
        Article(
            id="api-article-1",
            feed_id=feed.id,
            title="Pending Article",
            process_status="synced",
        ),
        Article(
            id="api-article-2",
            feed_id=feed.id,
            title="Failed Article",
            process_status="failed",
            process_stage="fetch",
            process_error="Test error",
        ),
        Article(
            id="api-article-3",
            feed_id=feed.id,
            title="Done Article",
            process_status="done",
        ),
    ]
    for article in articles:
        test_session.add(article)
    await test_session.commit()


@pytest.fixture
async def client(test_session_factory, setup_test_data):
    """创建测试客户端."""

    async def override_get_session():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


class TestProcessStatsEndpoint:
    """测试 /api/process/stats 端点."""

    async def test_returns_stats(self, client: AsyncClient) -> None:
        """返回正确的统计数据."""
        response = await client.get("/api/process/stats")
        assert response.status_code == 200
        data = response.json()
        assert "synced" in data
        assert "fetching" in data
        assert "pending_analysis" in data
        assert "analyzing" in data
        assert "done" in data
        assert "failed" in data
        assert "total" in data


class TestProcessProgressEndpoint:
    """测试 /api/process/progress 端点."""

    async def test_returns_progress(self, client: AsyncClient) -> None:
        """返回当前进度."""
        response = await client.get("/api/process/progress")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "total" in data
        assert "completed" in data
        assert "failed" in data


class TestProcessControlEndpoints:
    """测试处理控制端点."""

    @pytest.mark.skip(reason="需要完整的数据库初始化，移至 E2E 测试")
    async def test_start_returns_started_status(self, client: AsyncClient) -> None:
        """启动处理返回 started 状态（后台任务可能失败，但 API 响应正确）."""
        response = await client.post("/api/process/start")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["status"] in ["started", "running"]

    async def test_pause_when_not_running(self, client: AsyncClient) -> None:
        """未运行时暂停返回 idle."""
        response = await client.post("/api/process/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"

    async def test_stop_returns_stopped_or_idle(self, client: AsyncClient) -> None:
        """停止返回 stopped 或 idle."""
        response = await client.post("/api/process/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["stopped", "idle"]

    async def test_resume_when_not_running(self, client: AsyncClient) -> None:
        """未运行时恢复返回 idle."""
        response = await client.post("/api/process/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["idle", "running"]


class TestProcessFailedEndpoint:
    """测试 /api/process/failed 端点."""

    async def test_returns_failed_list(self, client: AsyncClient) -> None:
        """返回失败列表."""
        response = await client.get("/api/process/failed")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)
