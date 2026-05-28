"""WebSocket 端点 — 任务进度实时推送"""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/tasks/{task_id}")
async def task_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()

    # 从 Redis pub/sub 订阅任务进度
    redis = None
    pubsub = None
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"task:{task_id}:progress")

        await websocket.send_text(json.dumps({"type": "connected", "task_id": task_id}))

        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_text(
                    json.dumps({"type": "progress", "data": data})
                )
    except WebSocketDisconnect:
        pass
    finally:
        if pubsub:
            await pubsub.unsubscribe(f"task:{task_id}:progress")
