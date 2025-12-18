from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # URL до control-plane (управляющего сервера)
    CONTROL_PLANE_URL: str = "http://127.0.0.1:8000"

    # Идентификатор ноды в control-plane (нужно взять из /nodes в основном сервисе)
    NODE_ID: str = "CHANGE_ME_NODE_ID"

    # Необязательный секрет ноды — пока не используется, на будущее
    NODE_API_KEY: str = "CHANGE_ME_NODE_KEY"

    # Интервал отправки heartbeat в секундах
    HEARTBEAT_INTERVAL_SECONDS: int = 10

    model_config = SettingsConfigDict(env_file=".env.node", extra="ignore")


settings = Settings()
