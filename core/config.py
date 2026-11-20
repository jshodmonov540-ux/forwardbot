from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Bot sozlamalari
    BOT_TOKEN: str = Field(..., description="Telegram Bot Tokeni")
    BOT_USERNAME: Optional[str] = Field(None, description="Bot username (@ siz)")
    
    # Telegram API (Userbot / Telethon uchun)
    API_ID: Optional[int] = Field(default=None, description="Telegram API ID (my.telegram.org)")
    API_HASH: Optional[str] = Field(default=None, description="Telegram API Hash (my.telegram.org)")

    @field_validator("API_ID", mode="before")
    @classmethod
    def validate_api_id(cls, v):
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return int(v)

    @field_validator("API_HASH", mode="before")
    @classmethod
    def validate_api_hash(cls, v):
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()
    
    # Ma'lumotlar bazasi
    # Standart: PostgreSQL. Lokal testlar uchun sqlite+aiosqlite ham mumkin
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/forwardbot",
        description="Async SQLAlchemy database URL"
    )

    # Redis (ixtiyoriy)
    REDIS_URL: Optional[str] = Field(None, description="Redis URL, masalan redis://localhost:6379/0")

    # Xavfsizlik va ruxsatlar
    INVITE_CODE_REQUIRED: bool = Field(default=False, description="Faqat taklifnoma kodi bilan kirish")
    ADMIN_IDS: List[int] = Field(default_factory=list, description="Admin Telegram ID lari ro'yxati")
    
    # Webhook yoki Polling
    USE_WEBHOOK: bool = Field(default=False, description="Webhook rejimini yoqish")
    WEBHOOK_URL: Optional[str] = Field(None, description="Webhook URL")
    WEBHOOK_PATH: str = Field(default="/webhook", description="Webhook path")
    WEBHOOK_SECRET: Optional[str] = Field(None, description="Webhook maxfiy kaliti")
    WEBHOOK_HOST: str = Field(default="0.0.0.0", description="Webhook tinglovchi host")
    WEBHOOK_PORT: int = Field(default=8000, description="Webhook porti")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Loglash darajasi")


settings = Settings()
