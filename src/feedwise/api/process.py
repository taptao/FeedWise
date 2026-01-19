"""统一处理 API."""

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from feedwise.core.processor import (
    ProcessEngine,
    get_engine,
    get_failed_articles,
    get_process_stats,
    get_progress,
    register_ws,
    reset_failed_to_pending,
    unregister_ws,
)
from feedwise.models.database import get_session

router = APIRouter(prefix="/api/process", tags=["process"])


@router.get("/stats")
async def get_stats(
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """获取处理统计 - 流水线阶段."""
    stats = await get_process_stats(session)
    return {
        "synced": stats.synced,
        "fetching": stats.fetching,
        "pending_analysis": stats.pending_analysis,
        "analyzing": stats.analyzing,
        "done": stats.done,
        "failed": stats.failed,
        "total": stats.total,
    }


@router.get("/progress")
async def get_current_progress() -> dict[str, Any]:
    """获取当前处理进度."""
    progress = get_progress()
    return {
        "status": progress.status,
        "total": progress.total,
        "completed": progress.completed,
        "failed": progress.failed,
        "current_article": progress.current_article,
        "current_stage": progress.current_stage,
        "started_at": progress.started_at.isoformat() if progress.started_at else None,
    }


@router.post("/start")
async def start_processing(
    batch_size: int = 50,
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> dict[str, str]:
    """启动处理."""
    engine = get_engine()
    if engine and engine.is_running:
        return {"message": "处理已在运行中", "status": "running"}

    # 后台启动处理引擎
    new_engine = ProcessEngine()
    background_tasks.add_task(new_engine.start, batch_size)

    return {"message": "处理已启动", "status": "started"}


@router.post("/pause")
async def pause_processing() -> dict[str, str]:
    """暂停处理."""
    engine = get_engine()
    if not engine or not engine.is_running:
        return {"message": "没有正在运行的处理", "status": "idle"}

    engine.pause()
    return {"message": "处理已暂停", "status": "paused"}


@router.post("/resume")
async def resume_processing() -> dict[str, str]:
    """恢复处理."""
    engine = get_engine()
    if not engine:
        return {"message": "没有可恢复的处理", "status": "idle"}

    engine.resume()
    return {"message": "处理已恢复", "status": "running"}


@router.post("/stop")
async def stop_processing() -> dict[str, str]:
    """停止处理."""
    engine = get_engine()
    if not engine:
        return {"message": "没有正在运行的处理", "status": "idle"}

    engine.stop()
    return {"message": "处理已停止", "status": "stopped"}


@router.get("/failed")
async def get_failed(
    page: int = 1,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """获取失败的文章列表."""
    items, total = await get_failed_articles(session, page, limit)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items,
    }


@router.post("/retry")
async def retry_failed(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | int]:
    """重试失败的文章."""
    engine = get_engine()
    if engine and engine.is_running:
        return {"message": "处理正在运行中，请先停止", "reset_count": 0}

    reset_count = await reset_failed_to_pending(session)
    if reset_count == 0:
        return {"message": "没有失败的文章需要重试", "reset_count": 0}

    # 自动启动处理
    new_engine = ProcessEngine()
    background_tasks.add_task(new_engine.start, 50)

    return {
        "message": f"已重置 {reset_count} 篇文章，开始重新处理",
        "reset_count": reset_count,
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket 端点，实时推送处理进度."""
    await websocket.accept()
    register_ws(websocket)

    try:
        # 发送当前状态
        progress = get_progress()
        await websocket.send_json(
            {
                "type": "connected",
                "data": {
                    "status": progress.status,
                    "total": progress.total,
                    "completed": progress.completed,
                    "failed": progress.failed,
                },
            }
        )

        # 保持连接，等待消息或断开
        while True:
            try:
                # 等待客户端消息（心跳或命令）
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )
                # 处理心跳
                if data == "ping":
                    await websocket.send_text("pong")
            except TimeoutError:
                # 发送心跳检测
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    finally:
        unregister_ws(websocket)
