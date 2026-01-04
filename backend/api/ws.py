import asyncio
import contextlib
import json
from typing import Any

import redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from celery_worker import chat_turn_pubsub, run_analysis_pubsub
from core.config import REDIS_DB, REDIS_HOST, REDIS_PORT

router = APIRouter()


def _r():
    return redis.Redis(
        host=REDIS_HOST, port=int(REDIS_PORT), db=int(REDIS_DB), decode_responses=True
    )


@router.websocket("/ws/chats/{chat_id}")
async def ws_chat(websocket: WebSocket, chat_id: str):
    await websocket.accept()
    r = _r()
    pubsub = r.pubsub()
    channel = f"chat:{chat_id}"
    pubsub.subscribe(channel)

    async def reader():
        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data")
                    await websocket.send_text(data)
                await asyncio.sleep(0.01)
        except Exception:
            pass

    reader_task = asyncio.create_task(reader())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload: dict[str, Any] = json.loads(raw)
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "code": "bad_json"}))
                continue

            msg_type = payload.get("type")
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg_type == "analysis_start":
                request_id = payload.get("request_id") or f"ws-{id(payload)}"
                filters = payload.get("filters", {})
                prompt = payload.get("prompt")
                run_analysis_pubsub.delay(request_id, chat_id, filters, prompt)
                await websocket.send_text(
                    json.dumps({"type": "accepted", "request_id": request_id})
                )
            elif msg_type == "chat_turn":
                request_id = payload.get("request_id") or f"ws-{id(payload)}"
                content = payload.get("content", "")
                chat_turn_pubsub.delay(request_id, chat_id, content)
                await websocket.send_text(
                    json.dumps({"type": "accepted", "request_id": request_id})
                )
            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "code": "unsupported_message"})
                )
    except WebSocketDisconnect:
        pass
    finally:
        with contextlib.suppress(Exception):
            reader_task.cancel()
        with contextlib.suppress(Exception):
            pubsub.unsubscribe(channel)
            pubsub.close()
