from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import engine, Base, SessionLocal
from .routers import auth, nodes, rooms, billing, users
from .models import ServerNode, NodeStatus
from .config import settings

app = FastAPI(
    title="Quiet Rooms Control Plane",
    version="0.4.0",
)


@app.on_event("startup")
def on_startup() -> None:
    """Инициализируем схему БД при запуске приложения."""
    Base.metadata.create_all(bind=engine)

    if settings.DEMO_NODE_ENABLED:
        _ensure_demo_node()


def _ensure_demo_node() -> None:
    """Создаёт демо-ноду для локального запуска, если нод нет вообще."""
    db: Session = SessionLocal()
    try:
        exists = db.scalar(select(ServerNode.id).limit(1))
        if exists:
            return

        demo = ServerNode(
            name="demo-node",
            base_url=settings.DEMO_NODE_BASE_URL,
            max_rooms=settings.DEFAULT_NODE_MAX_ROOMS,
            status=NodeStatus.ACTIVE,
            api_key_hash="demo-key",
        )
        db.add(demo)
        db.commit()
    finally:
        db.close()

# -----------------------
# CORS — обязательно!
# -----------------------

origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "quiet rooms control-plane"}

app.include_router(auth.router)
app.include_router(nodes.router)
app.include_router(rooms.router)
app.include_router(billing.router)
app.include_router(users.router)
