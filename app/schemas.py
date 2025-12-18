from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, constr, field_validator


# ---------------------------
# Пользователи / Авторизация
# ---------------------------

class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    # длина 6–12
    password: constr(min_length=6, max_length=12)

    # только цифры
    @field_validator("password")
    def password_digits_only(cls, v: str):
        if not v.isdigit():
            raise ValueError("Пароль должен содержать только цифры")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class UserProfile(UserOut):
    """
    Профиль пользователя для /users/me.
    Сейчас = UserOut, но можно расширять (тариф, лимиты и т.п.).
    """
    pass


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"



class TokenData(BaseModel):
    user_id: str | None = None
    email: str | None = None



# ---------------------------
# Комнаты
# ---------------------------

class RoomBase(BaseModel):
    title: Optional[str] = None
    # на случай, если в модели поле называется name
    name: Optional[str] = None
    max_participants: int = 20


class RoomCreate(RoomBase):
    """
    При создании комнаты фронт отправляет title и name (одно и то же значение).
    Бэкенд может использовать room_in.title or room_in.name.
    """
    pass


class RoomUpdate(BaseModel):
    title: Optional[str] = None
    max_participants: Optional[int] = None


class RoomOut(BaseModel):
    id: int
    code: str
    title: Optional[str]
    owner_id: int
    max_participants: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RoomListOut(BaseModel):
    rooms: List[RoomOut]


class RoomNodeInfo(BaseModel):
    node_base_url: str
    room_code: str


# ---------------------------
# Ноды (media-сервера)
# ---------------------------

class NodeRegister(BaseModel):
    """
    Регистрация/создание ноды медиа-сервера.
    """
    node_id: str
    base_url: str
    capacity_rooms: int = 3  # максимум комнат на этой ноде


class NodeHeartbeat(BaseModel):
    """
    Пинг от ноды о текущей загрузке.
    """
    active_rooms: int
    cpu_load: Optional[float] = None
    mem_load: Optional[float] = None


class NodeOut(BaseModel):
    """
    То, что отдаём наружу как описание ноды.
    """
    id: int
    node_id: str
    base_url: str
    capacity_rooms: int
    active_rooms: int
    is_online: bool
    last_heartbeat: Optional[datetime]

    class Config:
        from_attributes = True


# ---- Совместимость со старым crud.py ----
# create_node(db, data: schemas.ServerNodeCreate)
# update_node(db, node, data: schemas.ServerNodeUpdate)
# heartbeat_node(db, node, hb: schemas.ServerNodeHeartbeat)
# и ответы schemas.ServerNodeOut

class ServerNodeCreate(NodeRegister):
    """
    Алиас для старого имени схемы:
    ServerNodeCreate == NodeRegister
    """
    pass


class ServerNodeUpdate(BaseModel):
    """
    Для обновления ноды: все поля опциональны.
    Подходит под update_node, где могут менять базовый URL, лимиты и т.п.
    """
    base_url: Optional[str] = None
    capacity_rooms: Optional[int] = None
    active_rooms: Optional[int] = None
    is_online: Optional[bool] = None


class ServerNodeHeartbeat(NodeHeartbeat):
    """
    Алиас для старого имени схемы:
    ServerNodeHeartbeat == NodeHeartbeat
    """
    pass


class ServerNodeOut(NodeOut):
    """
    Алиас для совместимости, если где-то используется ServerNodeOut.
    """
    pass


# ---------------------------
# Тарифы и подписки
# ---------------------------

class TariffPlanBase(BaseModel):
    code: str
    name: str
    monthly_price: int          # рубли
    included_rooms: int         # сколько комнат включено
    extra_room_price: int       # рубли за доп. комнату


class TariffPlanOut(TariffPlanBase):
    id: int

    class Config:
        from_attributes = True


class UserSubscriptionBase(BaseModel):
    plan_id: int
    rooms_limit: int
    active_until: Optional[datetime] = None


class UserSubscriptionOut(UserSubscriptionBase):
    id: int
    user_id: int
    is_active: bool

    class Config:
        from_attributes = True


# ---------------------------
# ЮKassa
# ---------------------------

class YookassaCreatePayment(BaseModel):
    """
    Параметры для инициации платежа:
    сумма, описание, return_url.
    """
    amount: int        # в рублях
    description: str
    return_url: str    # куда вернуть пользователя после оплаты


class YookassaPaymentOut(BaseModel):
    payment_id: str
    status: str
    confirmation_url: Optional[str] = None


# ---------------------------
# Общие простые ответы
# ---------------------------

class MessageOut(BaseModel):
    message: str
