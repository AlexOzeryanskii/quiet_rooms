from datetime import datetime
import secrets
import string
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db, get_current_user

router = APIRouter(prefix="/rooms", tags=["rooms"])

# Сколько комнат можно создать одному пользователю на текущем тарифе
MAX_ROOMS_PER_USER = 1


def generate_room_code(length: int = 6) -> str:
    """
    Генерирует короткий код комнаты: например, 'a7f3kx'.
    """
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def pick_media_node_for_new_room(db: Session) -> "models.MediaNode":
    """
    Выбираем медиасервер (ноду), на который можно повесить новую комнату.

    Ожидается, что в models есть класс MediaNode с полями:
    - id: int
    - base_url: str
    - is_online: bool
    - capacity_rooms: int
    - active_rooms: int
    """
    node = (
        db.query(models.MediaNode)
        .filter(models.MediaNode.is_online == True)  # noqa: E712
        .order_by(models.MediaNode.active_rooms.asc())
        .first()
    )

    if not node:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Нет доступных медиасерверов",
        )

    if node.active_rooms >= node.capacity_rooms:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Нет свободных серверов для создания комнаты",
        )

    return node


# ------------------------
# Список комнат текущего пользователя
# ------------------------


@router.get("/my", response_model=List[schemas.RoomOut])
def get_my_rooms(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Возвращает список комнат, созданных текущим пользователем.
    """
    rooms = (
        db.query(models.Room)
        .filter(models.Room.owner_id == current_user.id)
        .order_by(models.Room.created_at.desc())
        .all()
    )
    return rooms


# ------------------------
# Создание комнаты
# ------------------------


@router.post("/", response_model=schemas.RoomOut)
def create_room(
    room_in: schemas.RoomCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Создать комнату.

    Ограничения:
    - не более MAX_ROOMS_PER_USER комнат на пользователя.
    """
    # Проверка лимита комнат для пользователя
    existing_count = (
        db.query(models.Room)
        .filter(models.Room.owner_id == current_user.id)
        .count()
    )
    if existing_count >= MAX_ROOMS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Лимит комнат по текущему тарифу исчерпан. "
                "Удалите одну из комнат или обновите тариф."
            ),
        )

    # Название комнаты берём из title или name
    title = (room_in.title or room_in.name or "").strip()
    if not title:
        title = None

    # Выбираем медиасервер
    node = pick_media_node_for_new_room(db)

    # Генерируем уникальный код комнаты
    code = generate_room_code()
    while db.query(models.Room).filter(models.Room.code == code).first():
        code = generate_room_code()

    new_room = models.Room(
        code=code,
        title=title,
        owner_id=current_user.id,
        max_participants=room_in.max_participants,
        status="active",
        created_at=datetime.utcnow(),
        media_node_id=node.id,  # поле связи с нодой
    )

    db.add(new_room)

    # Увеличиваем счётчик активных комнат на ноде
    node.active_rooms += 1
    db.add(node)

    db.commit()
    db.refresh(new_room)

    return new_room


# ------------------------
# Информация о комнате по коду
# ------------------------


@router.get("/{code}", response_model=schemas.RoomOut)
def get_room_by_code(
    code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Получить информацию о комнате по её коду.
    Используется в основном ведущим (владелец комнаты).
    """
    room = db.query(models.Room).filter(models.Room.code == code).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Комната не найдена",
        )

    # При желании можно дополнительно ограничить доступ:
    # if room.owner_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Нет доступа к этой комнате")

    return room


# ------------------------
# Получить медиасервер (ноду) для комнаты
# ------------------------


@router.get("/{code}/node", response_model=schemas.RoomNodeInfo)
def get_room_node(
    code: str,
    db: Session = Depends(get_db),
):
    """
    Возвращает URL медиасервера, к которому нужно подключаться клиентам,
    и код комнаты.

    Логика:
    - находим комнату по коду;
    - если у комнаты уже задан media_node_id — берём эту ноду;
    - если нет — подбираем ноду с минимальной загрузкой и привязываем комнату к ней.
    """
    room = db.query(models.Room).filter(models.Room.code == code).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Комната не найдена",
        )

    node = None

    # Если комната уже привязана к ноде
    if getattr(room, "media_node_id", None):
        node = (
            db.query(models.MediaNode)
            .filter(models.MediaNode.id == room.media_node_id)
            .first()
        )
        # если почему-то нода пропала — выбираем свежую
        if not node:
            node = pick_media_node_for_new_room(db)
            room.media_node_id = node.id
            node.active_rooms += 1
            db.add(room)
            db.add(node)
            db.commit()
    else:
        # Старые комнаты без media_node_id — назначаем ноду
        node = pick_media_node_for_new_room(db)
        room.media_node_id = node.id
        node.active_rooms += 1
        db.add(room)
        db.add(node)
        db.commit()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось подобрать сервер для комнаты",
        )

    return schemas.RoomNodeInfo(
        node_base_url=node.base_url,
        room_code=room.code,
    )
