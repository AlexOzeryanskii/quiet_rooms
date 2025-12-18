import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./quiet_rooms.db"

    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DEFAULT_NODE_MAX_ROOMS: int = 3

    # Демонстрационная нода для локального запуска без внешних серверов
    DEMO_NODE_ENABLED: bool = True
    DEMO_NODE_BASE_URL: str = "http://127.0.0.1:9000"

    # --- YooKassa ---
    YOOKASSA_SHOP_ID: str = "YOUR_SHOP_ID"
    YOOKASSA_SECRET_KEY: str = "YOUR_SECRET_KEY"
    # URL, на который ЮKassa будет слать webhook (на бою: https://your.domain/api/billing/yookassa/webhook)
    YOOKASSA_WEBHOOK_URL: str = "https://example.com/api/billing/yookassa/webhook"

    # Цена комнаты (в рублях)
    ROOM_PRICE_RUB: int = 1200

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
