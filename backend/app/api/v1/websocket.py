import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections grouped by org_id for multi-tenant isolation."""

    def __init__(self):
        self.active: Dict[str, Set[WebSocket]] = {}  # org_id -> set of websockets
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, org_id: str):
        """Register a websocket connection under an organization."""
        async with self._lock:
            if org_id not in self.active:
                self.active[org_id] = set()
            self.active[org_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, org_id: str):
        """Remove a websocket connection."""
        async with self._lock:
            if org_id in self.active:
                self.active[org_id].discard(websocket)
                if not self.active[org_id]:
                    del self.active[org_id]

    async def broadcast_to_org(self, org_id: str, message: dict):
        """Send a message to all connections in an organization."""
        async with self._lock:
            connections = self.active.get(org_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(ws, org_id)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    @property
    def connection_count(self) -> int:
        """Total active connections across all orgs."""
        return sum(len(conns) for conns in self.active.values())


manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Live event stream + alert notifications.

    Protocol:
    1. Client connects via WebSocket
    2. Client sends auth message: {"token": "<jwt_access_token>"}
    3. Server validates token and sends: {"type": "connected", "org_id": "..."}
    4. Server pushes real-time events and alerts to the client
    5. Client can send {"type": "ping"} and will receive {"type": "pong"}
    """
    await websocket.accept()
    org_id = ""

    # ─── Authentication Phase ────────────────────
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        data = json.loads(raw)
        token = data.get("token", "")
    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Authentication timeout")
        return
    except Exception:
        await websocket.close(code=4001, reason="Invalid auth message")
        return

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    org_id = payload.get("org_id", "")
    if not org_id:
        await websocket.close(code=4003, reason="No organization context in token")
        return

    # ─── Connected ────────────────────────────────
    await manager.connect(websocket, org_id)
    await websocket.send_json({"type": "connected", "org_id": org_id})

    # ─── Message Loop ─────────────────────────────
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "subscribe":
                # Future: subscribe to specific event channels
                await websocket.send_json({"type": "subscribed", "channel": data.get("channel")})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(websocket, org_id)
