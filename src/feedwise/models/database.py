"""数据库初始化和会话管理."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

# 全局引擎和会话工厂
_engine: Any = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(database_url: str) -> None:
    """初始化数据库，创建所有表."""
    global _engine, _session_factory

    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于依赖注入）."""
    if _session_factory is None:
        msg = "数据库未初始化，请先调用 init_db()"
        raise RuntimeError(msg)

    async with _session_factory() as session:
        yield session


def async_session_maker() -> async_sessionmaker[AsyncSession]:
    """获取会话工厂（用于后台任务）."""
    if _session_factory is None:
        msg = "数据库未初始化，请先调用 init_db()"
        raise RuntimeError(msg)
    return _session_factory
