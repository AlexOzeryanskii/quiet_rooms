from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings
from .schemas import TokenData

# Используем pbkdf2_sha256 — надёжно и без проблем с длиной
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    data должен содержать хотя бы:
    {
        "sub": user.id,   # строка
        "email": user.email
    }
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Декодируем токен и всегда возвращаем user_id как СТРОКУ.
    Это критично для SQLite и нашего String primary key.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id_raw = payload.get("sub")
        email = payload.get("email")

        if user_id_raw is None:
            return None

        # Жёстко приводим к строке, даже если внутри UUID
        user_id_str = str(user_id_raw)

        return TokenData(user_id=user_id_str, email=email)
    except JWTError:
        return None
