import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4

import httpx
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

from .config import settings
from .models import node_state, LocalRoom, NodeState
from .deps import get_node_state


app = FastAPI(
    title="Quiet Rooms Node Service",
    version="0.4.0",
)


# ---------- Pydantic-схемы ----------

class NodeInfo(BaseModel):
    node_id: str
    active_rooms: int
    cpu_load: float | None = None
    mem_load: float | None = None
    timestamp: datetime


class LocalRoomCreate(BaseModel):
    title: Optional[str] = None
    max_participants: int = 20


class LocalRoomOut(BaseModel):
    code: str
    title: Optional[str]
    max_participants: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Память ноды ----------

# room_code -> { client_id -> WebSocket }
room_clients: Dict[str, Dict[str, WebSocket]] = {}

# room_code -> { client_id -> meta }
room_participants_meta: Dict[str, Dict[str, dict]] = {}


# ---------- Heartbeat ----------

async def send_heartbeat_loop():
    await asyncio.sleep(2)
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                active_rooms = node_state.active_rooms_count()
                payload = {
                    "active_rooms": active_rooms,
                    "cpu_load": node_state.cpu_load,
                    "mem_load": node_state.mem_load,
                }
                url = f"{settings.CONTROL_PLANE_URL}/nodes/{settings.NODE_ID}/heartbeat"
                await client.post(url, json=payload)
            except Exception as e:
                print(f"[{datetime.utcnow().isoformat()}] Heartbeat error: {e}")
            await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SECONDS)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(send_heartbeat_loop())


async def broadcast_participants(room_code: str) -> None:
    """Рассылаем всем участникам комнаты список участников."""
    clients = room_clients.get(room_code)
    if not clients:
        return

    meta = room_participants_meta.get(room_code, {})
    participants = [
        {
            "id": client_id,
            "name": meta.get(client_id, {}).get("name", "Гость"),
        }
        for client_id in clients.keys()
    ]

    message = json.dumps(
        {
            "type": "participants",
            "participants": participants,
        }
    )

    for ws in list(clients.values()):
        try:
            await ws.send_text(message)
        except Exception:
            pass


# ---------- HTTP-эндпоинты ноды ----------

@app.get("/health")
def health():
    return {"status": "ok", "node_id": settings.NODE_ID}


@app.get("/node-info", response_model=NodeInfo)
def get_node_info(state: NodeState = Depends(get_node_state)):
    return NodeInfo(
        node_id=settings.NODE_ID,
        active_rooms=state.active_rooms_count(),
        cpu_load=state.cpu_load,
        mem_load=state.mem_load,
        timestamp=datetime.utcnow(),
    )


@app.get("/rooms", response_model=List[LocalRoomOut])
def list_rooms(state: NodeState = Depends(get_node_state)):
    return [
        LocalRoomOut(
            code=r.code,
            title=r.title,
            max_participants=r.max_participants,
            created_at=r.created_at,
            is_active=r.is_active,
        )
        for r in state.rooms.values()
    ]


@app.post("/rooms/{code}/start", response_model=LocalRoomOut, status_code=status.HTTP_201_CREATED)
def start_room(
    code: str,
    data: LocalRoomCreate,
    state: NodeState = Depends(get_node_state),
):
    if code in state.rooms:
        room = state.rooms[code]
        room.is_active = True
        return LocalRoomOut(
            code=room.code,
            title=room.title,
            max_participants=room.max_participants,
            created_at=room.created_at,
            is_active=room.is_active,
        )

    room = LocalRoom(
        code=code,
        title=data.title,
        max_participants=data.max_participants,
    )
    state.rooms[code] = room
    return LocalRoomOut(
        code=room.code,
        title=room.title,
        max_participants=room.max_participants,
        created_at=room.created_at,
        is_active=room.is_active,
    )


@app.post("/rooms/{code}/stop", response_model=LocalRoomOut)
def stop_room(
    code: str,
    state: NodeState = Depends(get_node_state),
):
    room = state.rooms.get(code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found on this node")

    room.is_active = False
    return LocalRoomOut(
        code=room.code,
        title=room.title,
        max_participants=room.max_participants,
        created_at=room.created_at,
        is_active=room.is_active,
    )


# ---------- WebSocket: сигналинг + управление + чат ----------

@app.websocket("/ws/rooms/{code}")
async def room_websocket(code: str, websocket: WebSocket):
    """
    WebSocket для комнаты:
      - type="participants" — список участников
      - type="signal"      — WebRTC-сигналинг (offer/answer/ice)
      - type="control"     — управляющие команды (разрешение видео, блокировка и т.п.)
      - type="chat"        — текстовый чат
    """
    await websocket.accept()

    client_id = websocket.query_params.get("client_id") or str(uuid4())
    name = websocket.query_params.get("name") or "Гость"

    clients = room_clients.setdefault(code, {})
    meta = room_participants_meta.setdefault(code, {})

    clients[client_id] = websocket
    meta[client_id] = {
        "name": name,
        "joined_at": datetime.utcnow().isoformat(),
    }

    await broadcast_participants(code)

    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "signal":
                target_id = data.get("to")
                if not target_id:
                    continue
                target_ws = clients.get(target_id)
                if target_ws:
                    await target_ws.send_text(json.dumps(data))

            elif msg_type == "control":
                # управляющие сообщения: {type:"control", to, from, action, payload}
                target_id = data.get("to")
                if target_id:
                    target_ws = clients.get(target_id)
                    if target_ws:
                        await target_ws.send_text(json.dumps(data))
                else:
                    # broadcast по комнате, если to не указан
                    for ws in list(clients.values()):
                        try:
                            await ws.send_text(json.dumps(data))
                        except Exception:
                            pass

            elif msg_type == "chat":
                # Простой чат: ретранслируем всем в комнате
                text_msg = data.get("text")
                if not text_msg:
                    continue

                author_name = data.get("name") or meta.get(client_id, {}).get("name", "Гость")

                envelope = json.dumps(
                    {
                        "type": "chat",
                        "from": client_id,
                        "name": author_name,
                        "text": text_msg,
                        "ts": datetime.utcnow().isoformat(),
                    }
                )
                for ws in list(clients.values()):
                    try:
                        await ws.send_text(envelope)
                    except Exception:
                        pass

            else:
                # другие типы можно реализовать позже (чат, статус, и т.п.)
                pass

    except WebSocketDisconnect:
        pass
    finally:
        clients = room_clients.get(code, {})
        meta = room_participants_meta.get(code, {})

        clients.pop(client_id, None)
        meta.pop(client_id, None)

        if not clients:
            room_clients.pop(code, None)
            room_participants_meta.pop(code, None)
        else:
            await broadcast_participants(code)
