import secrets
import string
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .models import NodeStatus, RoomStatus, User, UserSubscription
from .auth import hash_password, verify_password


class RoomLimitExceeded(Exception):
    """Лимит комнат для пользователя исчерпан."""


class NodeUnavailable(Exception):
    """Нет подходящей ноды для создания комнаты."""


# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------

def generate_room_code(length: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ---------- USERS ----------

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    return db.scalars(stmt).first()


def create_user(db: Session, user_in: schemas.UserCreate) -> User:
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        max_rooms=1,  # по умолчанию 1 комната по подписке
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Базовая запись подписки (потом привяжем к ЮKassa)
    sub = UserSubscription(
        user_id=user.id,
        room_count=1,
        status="active",
        amount_rub=0,
        description="Initial free room or base subscription",
    )
    db.add(sub)
    db.commit()
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_active_room_limit(db: Session, user: User) -> int:
    """
    Сколько комнат пользователю разрешено по подпискам.
    Сейчас берём из user.max_rooms.
    Можно заменить на сумму активных UserSubscription.room_count.
    """
    return user.max_rooms


def get_user_active_room_count(db: Session, user: User) -> int:
    stmt = select(models.Room).where(
        models.Room.owner_id == user.id,
        models.Room.is_deleted == False,
        models.Room.status != RoomStatus.CLOSED,
    )
    return len(list(db.scalars(stmt)))


def list_user_rooms(db: Session, user: User) -> list[models.Room]:
    stmt = select(models.Room).where(
        models.Room.owner_id == user.id,
        models.Room.is_deleted == False,
    ).order_by(models.Room.created_at.desc())
    return list(db.scalars(stmt))


# ---------- NODES ----------

def create_node(db: Session, data: schemas.ServerNodeCreate) -> models.ServerNode:
    api_key_hash = data.api_key  # TODO: заменить на реальный хэш, если нужно

    node = models.ServerNode(
        name=data.name,
        base_url=str(data.base_url),
        max_rooms=data.max_rooms,
        api_key_hash=api_key_hash,
        status=NodeStatus.ACTIVE,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def list_nodes(db: Session) -> list[models.ServerNode]:
    stmt = select(models.ServerNode).order_by(models.ServerNode.created_at)
    return list(db.scalars(stmt))


def get_node(db: Session, node_id: str) -> Optional[models.ServerNode]:
    return db.get(models.ServerNode, node_id)


def update_node(db: Session, node: models.ServerNode, data: schemas.ServerNodeUpdate) -> models.ServerNode:
    payload = data.model_dump(exclude_unset=True)
    api_key = payload.pop("api_key", None)

    for field, value in payload.items():
        setattr(node, field, value)

    if api_key is not None:
        node.api_key_hash = api_key
    db.commit()
    db.refresh(node)
    return node


def update_node_heartbeat(
    db: Session,
    node: models.ServerNode,
    hb: schemas.ServerNodeHeartbeat,
) -> models.ServerNode:
    node.active_rooms = hb.active_rooms
    node.cpu_load = hb.cpu_load
    node.mem_load = hb.mem_load
    node.last_heartbeat = datetime.utcnow()
    db.commit()
    db.refresh(node)
    return node


def pick_node_for_new_room(db: Session) -> Optional[models.ServerNode]:
    """
    Простая стратегия: взять активную ноду с наименьшим количеством активных комнат,
    у которой active_rooms < max_rooms.
    """
    stmt = (
        select(models.ServerNode)
        .where(models.ServerNode.status == NodeStatus.ACTIVE)
        .where(models.ServerNode.active_rooms < models.ServerNode.max_rooms)
        .order_by(models.ServerNode.active_rooms.asc())
    )
    return db.scalars(stmt).first()


# ---------- ROOMS ----------

def create_room(db: Session, data: schemas.RoomCreate, owner: User) -> models.Room:
    # Проверяем лимит комнат по подписке
    limit = get_user_active_room_limit(db, owner)
    current = get_user_active_room_count(db, owner)
    if current >= limit:
        raise RoomLimitExceeded("Превышен лимит комнат по подписке. Докупите ещё одну комнату.")

    node = pick_node_for_new_room(db)
    if not node:
        raise NodeUnavailable("Нет доступных серверов для создания комнаты")

    code = generate_room_code()
    while db.scalar(select(models.Room).where(models.Room.code == code)):
        code = generate_room_code()

    title = (data.title or data.name or None)
    if title:
        title = title.strip() or None

    room = models.Room(
        code=code,
        title=title,
        owner_id=owner.id,
        node_id=node.id,
        max_participants=data.max_participants,
        status=RoomStatus.ACTIVE,
    )
    db.add(room)
    node.active_rooms += 1

    db.commit()
    db.refresh(room)
    return room


def get_room_by_code(db: Session, code: str) -> Optional[models.Room]:
    stmt = select(models.Room).where(
        models.Room.code == code,
        models.Room.is_deleted == False,
    )
    return db.scalars(stmt).first()


def close_room(db: Session, room: models.Room) -> models.Room:
    room.status = RoomStatus.CLOSED
    if room.node and room.node.active_rooms > 0:
        room.node.active_rooms -= 1
    db.commit()
    db.refresh(room)
    return room


# ---------- BILLING / SUBSCRIPTIONS ----------

def create_subscription_record_for_room(
    db: Session,
    user: User,
    external_id: str | None,
    amount_rub: int,
    description: str,
) -> UserSubscription:
    sub = UserSubscription(
        user_id=user.id,
        room_count=1,
        status="active",
        provider="yookassa",
        external_id=external_id,
        amount_rub=amount_rub,
        description=description,
    )
    db.add(sub)

    # увеличиваем доступный лимит комнат
    user.max_rooms += 1

    db.commit()
    db.refresh(sub)
    return sub
