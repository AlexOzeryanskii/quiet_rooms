import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    Enum,
    ForeignKey,
    Boolean,
    Float,
)
from sqlalchemy.orm import relationship

from .database import Base


class NodeStatus(str, PyEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    OFFLINE = "offline"


class RoomStatus(str, PyEnum):
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CLOSED = "closed"


class User(Base):
    __tablename__ = "users"

    # Строковый UUID как первичный ключ
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Сколько комнат ему разрешено по подписке (простая модель)
    max_rooms = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    rooms = relationship("Room", back_populates="owner")
    subscriptions = relationship("UserSubscription", back_populates="user")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Сколько комнат покрывает подписка (по 1 комнате за 1200 ₽)
    room_count = Column(Integer, default=1, nullable=False)

    # active / cancelled / pending
    status = Column(String, default="active", nullable=False)

    # Данные платёжного провайдера (ЮKassa и т.д.)
    provider = Column(String, default="yookassa", nullable=False)
    external_id = Column(String, nullable=True)  # payment_id или subscription_id

    # Финансовые данные
    amount_rub = Column(Integer, default=0, nullable=False)
    description = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="subscriptions")


class ServerNode(Base):
    __tablename__ = "server_nodes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)  # например, "https://node1.example.com"

    # Храним хэш/ключ ноды (пока можно хранить как есть, позже заменить на хэш)
    api_key_hash = Column(String, nullable=True)

    status = Column(Enum(NodeStatus), default=NodeStatus.ACTIVE, nullable=False)

    max_rooms = Column(Integer, default=3, nullable=False)
    active_rooms = Column(Integer, default=0, nullable=False)

    last_heartbeat = Column(DateTime, nullable=True)
    cpu_load = Column(Float, nullable=True)
    mem_load = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    rooms = relationship("Room", back_populates="node")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # короткий код комнаты для URL
    code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)

    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="rooms")

    node_id = Column(String, ForeignKey("server_nodes.id"), nullable=False)
    node = relationship("ServerNode", back_populates="rooms")

    max_participants = Column(Integer, default=20, nullable=False)
    status = Column(Enum(RoomStatus), default=RoomStatus.ACTIVE, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
