from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from redis.asyncio import Redis

from backend.celery_worker import chat_turn_pubsub, run_analysis_pubsub
from backend.core.config import get_settings
from backend.services.tokens import verify_chat_token

router = APIRouter()
_MAX_WS_MESSAGE_BYTES = 64 * 1024  # 64 KiB


def _validate_size(raw: str) -> bool:
    try:
        return len(raw.encode("utf-8")) <= _MAX_WS_MESSAGE_BYTES
    except Exception:
        return False


def _settings():
    return get_settings()


def _r() -> Redis:
    s = _settings()
    return Redis(
        host=s.REDIS_HOST,
        port=int(s.REDIS_PORT),
        db=int(s.REDIS_DB),
        password=(s.REDIS_PASSWORD or None),
        decode_responses=True,
        health_check_interval=30,
        socket_timeout=3.0,
        socket_connect_timeout=2.0,
        retry_on_timeout=True,
    )


async def _send_json(ws: WebSocket, payload: dict[str, Any]) -> None:
    await ws.send_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


async def _send_err(ws: WebSocket, code: str, detail: str | None = None) -> None:
    await _send_json(ws, {"type": "error", "code": code, **({"detail": detail} if detail else {})})


@router.websocket("/ws/chats/{chat_id}")
async def ws_chat(websocket: WebSocket, chat_id: str):
    await websocket.accept()

    # --- auth токен ---
    token = websocket.query_params.get("token")
    if not token:
        await _send_err(websocket, "no_token")
        await websocket.close(code=1008)
        return

    ok, claims, err = verify_chat_token(token)
    if not ok or (claims is None or claims.get("chat_id") != chat_id):
        await _send_err(websocket, err or "forbidden")
        await websocket.close(code=1008)
        return

    # --- pubsub ---
    r = _r()
    pubsub = r.pubsub()
    channel = f"chat:{chat_id}"
    await pubsub.subscribe(channel)

    async def reader():
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    data = msg.get("data")
                    if data is not None:
                        await websocket.send_text(data)
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("ws reader failed: {}", e)

    reader_task = asyncio.create_task(reader())

    await _send_json(websocket, {"type": "ready", "chat_id": chat_id})

    try:
        while True:
            raw = await websocket.receive_text()

            if not _validate_size(raw):
                await _send_err(websocket, "payload_too_large")
                continue

            try:
                payload: dict[str, Any] = json.loads(raw)
            except Exception:
                await _send_err(websocket, "bad_json")
                continue

            msg_type = payload.get("type")
            if not isinstance(msg_type, str):
                await _send_err(websocket, "bad_type")
                continue

            if msg_type == "ping":
                await _send_json(websocket, {"type": "pong"})
                continue

            if msg_type == "analysis_start":
                request_id = payload.get("request_id") or f"ws-{uuid.uuid4()}"
                filters = payload.get("filters") or {}
                if not isinstance(filters, dict):
                    await _send_err(websocket, "bad_filters")
                    continue
                prompt = payload.get("prompt")
                try:
                    run_analysis_pubsub.delay(request_id, chat_id, filters, prompt)
                except Exception as e:
                    logger.exception("Failed to enqueue analysis task")
                    await _send_err(websocket, "queue_unavailable", str(e))
                    continue
                await _send_json(websocket, {"type": "accepted", "request_id": request_id})
                continue

            if msg_type == "chat_turn":
                request_id = payload.get("request_id") or f"ws-{uuid.uuid4()}"
                content = payload.get("content", "")
                if not isinstance(content, str) or not content.strip():
                    await _send_err(websocket, "empty_content")
                    continue
                try:
                    chat_turn_pubsub.delay(request_id, chat_id, content)
                except Exception as e:
                    logger.exception("Failed to enqueue chat_turn task")
                    await _send_err(websocket, "queue_unavailable", str(e))
                    continue
                await _send_json(websocket, {"type": "accepted", "request_id": request_id})
                continue

            await _send_err(websocket, "unsupported_message")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("ws handler failed: {}", e)
    finally:
        with contextlib.suppress(Exception):
            reader_task.cancel()
            await reader_task
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        with contextlib.suppress(Exception):
            await r.close()
