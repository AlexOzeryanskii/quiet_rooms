from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..crud import NodeUnavailable, RoomLimitExceeded
from ..deps import get_db, get_current_user

router = APIRouter(prefix="/rooms", tags=["rooms"])


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
    return crud.list_user_rooms(db, current_user)


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
    Создать комнату, соблюдая лимиты подписки.
    """
    try:
        return crud.create_room(db, room_in, current_user)
    except RoomLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except NodeUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


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
    room = crud.get_room_by_code(db, code)
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
    - возвращаем информацию о ноде, на которой размещена комната.
    """
    room = crud.get_room_by_code(db, code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Комната не найдена",
        )

    node = room.node or db.get(models.ServerNode, room.node_id)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось подобрать сервер для комнаты",
        )

    return schemas.RoomNodeInfo(
        node_base_url=node.base_url,
        room_code=room.code,
    )
