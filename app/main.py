from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import auth, nodes, rooms, billing, users

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Quiet Rooms Control Plane",
    version="0.4.0",
)

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
