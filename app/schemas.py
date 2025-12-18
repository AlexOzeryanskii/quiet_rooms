from datetime import datetime
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, EmailStr, constr, field_validator
from .models import NodeStatus, RoomStatus


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
    id: str
    max_rooms: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfile(UserOut):
    """
    Профиль пользователя для /users/me.
    """

    current_rooms: int
    room_limit: int


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
    id: str
    code: str
    title: Optional[str]
    owner_id: str
    node_id: str
    max_participants: int
    status: RoomStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoomListOut(BaseModel):
    rooms: List[RoomOut]


class RoomNodeInfo(BaseModel):
    node_base_url: str
    room_code: str


# ---------------------------
# Ноды (media-сервера)
# ---------------------------

class ServerNodeCreate(BaseModel):
    """
    Создание ноды медиа-сервера.
    """

    name: str
    base_url: AnyHttpUrl
    max_rooms: int = 3
    api_key: Optional[str] = None


class ServerNodeUpdate(BaseModel):
    """
    Для обновления ноды: все поля опциональны.
    """

    name: Optional[str] = None
    base_url: Optional[AnyHttpUrl] = None
    max_rooms: Optional[int] = None
    active_rooms: Optional[int] = None
    status: Optional[NodeStatus] = None
    api_key: Optional[str] = None


class ServerNodeHeartbeat(BaseModel):
    """
    Пинг от ноды о текущей загрузке.
    """

    active_rooms: int
    cpu_load: Optional[float] = None
    mem_load: Optional[float] = None


class ServerNodeOut(BaseModel):
    """
    То, что отдаём наружу как описание ноды.
    """

    id: str
    name: str
    base_url: AnyHttpUrl
    status: NodeStatus
    max_rooms: int
    active_rooms: int
    cpu_load: Optional[float] = None
    mem_load: Optional[float] = None
    last_heartbeat: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    id: str

    model_config = ConfigDict(from_attributes=True)


class UserSubscriptionOut(BaseModel):
    id: str
    user_id: str
    room_count: int
    status: str
    provider: str
    external_id: Optional[str] = None
    amount_rub: int
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
