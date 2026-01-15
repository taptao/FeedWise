"""数据库初始化和会话管理."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

logger = logging.getLogger(__name__)

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

    # 执行数据迁移
    await _migrate_process_status()


async def _migrate_process_status() -> None:
    """迁移旧 fetch_status 到新 process_status."""
    if _session_factory is None:
        return

    async with _session_factory() as session:
        # 检查是否需要迁移（查找 process_status 为 synced 但 fetch_status 不为空的记录）
        check_sql = text("""
            SELECT COUNT(*) FROM articles
            WHERE process_status = 'synced'
            AND fetch_status IS NOT NULL
        """)
        result = await session.execute(check_sql)
        count = result.scalar()

        if not count or count == 0:
            return

        logger.info(f"迁移 {count} 条记录的 process_status")

        # 映射旧状态到新状态
        # fetch_status: pending -> process_status: pending_fetch
        # fetch_status: success -> process_status: pending_analysis (需要分析)
        # fetch_status: failed -> process_status: failed, process_stage: fetch
        # fetch_status: skipped -> process_status: pending_analysis

        await session.execute(
            text("""
            UPDATE articles SET process_status = 'pending_fetch'
            WHERE fetch_status = 'pending' AND process_status = 'synced'
        """)
        )

        await session.execute(
            text("""
            UPDATE articles SET process_status = 'pending_analysis'
            WHERE fetch_status = 'success' AND process_status = 'synced'
        """)
        )

        await session.execute(
            text("""
            UPDATE articles SET process_status = 'pending_analysis'
            WHERE fetch_status = 'skipped' AND process_status = 'synced'
        """)
        )

        await session.execute(
            text("""
            UPDATE articles SET process_status = 'failed', process_stage = 'fetch'
            WHERE fetch_status = 'failed' AND process_status = 'synced'
        """)
        )

        await session.commit()
        logger.info("process_status 迁移完成")


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
