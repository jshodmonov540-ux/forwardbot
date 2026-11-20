from datetime import datetime, timezone
import enum
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base


class TransactionType(str, enum.Enum):
    INFLOW = "INFLOW"    # Kirim
    OUTFLOW = "OUTFLOW"  # Chiqim


class TransactionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EDITED = "EDITED"
    DELETED = "DELETED"


class DestinationType(str, enum.Enum):
    PRIVATE = "PRIVATE"
    GROUP = "GROUP"
    CHANNEL = "CHANNEL"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user_id
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Rozilik
    is_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    agreed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Holat
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Telegram Business Connection
    business_connection_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    business_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Userbot (Telethon / QR-kod orqali)
    session_string: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_userbot_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Maqsad (Qayerga yuborish kerak)
    destination_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    destination_type: Mapped[str] = mapped_column(String(32), default=DestinationType.PRIVATE.value)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Bog'lanishlar (CASCADE DELETE)
    sources: Mapped[List["SourceWhitelist"]] = relationship("SourceWhitelist", back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    unparsed_counters: Mapped[List["UnparsedCounter"]] = relationship("UnparsedCounter", back_populates="user", cascade="all, delete-orphan")


class SourceWhitelist(Base):
    """
    Foydalanuvchi ruxsat bergan shaxsiy chatlar ro'yxati (Whitelist).
    Faqat shu chatlardan kelgan business_message qayta ishlanadi.
    """
    __tablename__ = "source_whitelists"
    __table_args__ = (
        UniqueConstraint("user_id", "chat_id", name="uq_user_source_chat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="sources")


class Transaction(Base):
    """
    Qayta ishlangan tranzaksiya ma'lumotlari.
    XAVFSIZLIK: Asl matn saqlanmaydi! Faqat summa, tur, vaqt va status.
    """
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "source_chat_id", "business_message_id", name="uq_user_source_msg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    business_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    tx_type: Mapped[str] = mapped_column(String(16), nullable=False)  # INFLOW / OUTFLOW
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(16), default="UZS")
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    status: Mapped[str] = mapped_column(String(16), default=TransactionStatus.ACTIVE.value)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="transactions")


class UnparsedCounter(Base):
    """
    Aniqlanmagan xabarlar hisoblagichi.
    XAVFSIZLIK: Aniqlanmagan xabar matni logga ham, bazaga ham yozilmaydi, faqat soni oshadi.
    """
    __tablename__ = "unparsed_counters"
    __table_args__ = (
        UniqueConstraint("user_id", "source_chat_id", name="uq_user_source_unparsed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="unparsed_counters")


class InviteCode(Base):
    """
    Tizimga kirish uchun adminlar yaratadigan taklifnoma kodlari.
    """
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
