"""
WebSocket handler — real-time slot availability updates via Redis pub/sub fanout.

Route:
  WS /ws/fields/{field_id}
     — subscribe to Redis channel field:{field_id}:slots
     — forward every SlotUpdateMessage JSON to connected client
     — unsubscribe and close on disconnect

Requirements: 5.1, 5.2, 5.3
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio.client import PubSub

from app.redis_client import get_redis, field_slots_channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/fields/{field_id}")
async def field_slot_ws(websocket: WebSocket, field_id: str):
    """
    Accept a WebSocket connection and stream slot status updates for the given field.

    Subscribes to Redis pub/sub channel `field:{field_id}:slots`. Every message
    published by the backend (slot status change) is forwarded as-is to the client.

    Reconnection with exponential backoff is handled client-side (mobile app).
    """
    await websocket.accept()
    logger.info("WebSocket connected: field=%s", field_id)

    redis = await get_redis()
    channel = field_slots_channel(field_id)

    pubsub: PubSub = redis.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                await websocket.send_text(data)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: field=%s", field_id)
    except Exception as exc:
        logger.error("WebSocket error for field=%s: %s", field_id, exc)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass
