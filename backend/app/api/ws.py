import asyncio
import logging
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
import jwt

from app.config import settings
from app.core.events import redis_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])

class ConnectionManager:
    def __init__(self):
        # Maps org_id (int) to lists of active websocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Keep track of active Redis listening tasks per organization
        self.redis_tasks: Dict[int, asyncio.Task] = {}

        async def connect(self, websocket: WebSocket, org_id: int):
            await websocket.accept()
            if org_id not in self.active_connections:
                self.active_connections[org_id] = []

            self.active_connections[org_id].append(websocket)
            logger.info(f"New WebSocket connection accepted for Org #{org_id}. Total active: {len(self.active_connections[org_id])}")

            # start listening to Redis events for this organization if we aren't already
            if org_id not in self.redis_tasks or self.redis_tasks[org_id].done():
                self.redis_tasks[org_id] = asyncio.create_task(self._listen_to_redis(org_id))

    def disconnect(self, websocket: WebSocket, org_id: int):
        if org_id in self.active_connections:
            if websocket in self.active_connections[org_id]:
                self.active_connections[org_id].remove(websocket)

            logger.info(f"WebSocket disconnected for Org # {org_id}. Active remaining: {len(self.active_connections[org_id])}")

            # if no one is connected in this organization, stop the Redis listener
            if not self.active_connections[org_id]:
                del self.active_connections[org_id]
                if org_id in self.redis_tasks:
                    self.redis_tasks[org_id].cancel()
                    del self.redis_tasks[org_id]
                    logger.info(f"Cancelled Redis Subscription listener for Org # {org_id}")

    async def _listen_to_redis(self, org_id: int):
        """
        Subscribes to the Redis channel for the organization
        and forwards any incoming broadcast events to all open WebSockets.
        """
        channel_name = f"org:{org_id}"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel_name)
        logger.info(f"Subscribed to Redis channel: '{channel_name}'")

        try:
            while True:
                # Wait for a new message on the channel (with a small timeout to yield execution)
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message["data"]
                    logger.info(f"Broadcasting Redis event from channel '{channel_name}' to open sockets.")

                    # send the raw message text to all connected sockets in this organization
                    if org_id in self.active_connections:
                        # copy list to iterate safely during disconnect changes
                        for ws in list(self.active_connections[org_id]):
                            try:
                                await ws.send_text(data)
                            except Exception as e:
                                logger.error(f"Failed to write to socket, disconnecting client: {e}")
                                self.disconnect(ws, org_id)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logger.info(f"Redis listener task cancelled for Org #{org_id}")
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()

manager = ConnectionManager()

def decode_ws_token(token: str) -> dict:
    """Helper to decode and validate JWT query token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
        return payload
    except Exception:
        raise ValueError("Invalid credentials")

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    Main WebSocket entrypoint.
    Mounts ws://localhost:8001/ws?token=<JWT_TOKEN>
    """
    try:
        payload = decode_ws_token(token)
        org_id = int(payload.get("org_id"))
    except Exception as e:
        logger.warning(f"Websocket rejected: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, org_id)

    try:
        while True:
            # We must keep the connection open by listening for any client heartbeats or messages.
            # if the client closes the tab, this raises WebSocketDisconnect
            data = await websocket.receive_text()
            # Respond back to keep-alives if necessary (otherwise ignore)
    except WebSocketDisconnect:
        manager.disconnect(websocket, org_id)
    except Exception as e:
        logger.error(f"WebSocket execution error: {e}")
        manager.disconnect(websocket, org_id)