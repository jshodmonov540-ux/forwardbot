import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from db.base import Base
from db.models import DestinationType, TransactionStatus, TransactionType
from db import crud


@pytest_asyncio.fixture
async def db_session():
    # SQLite in-memory engine for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_user_creation_and_agreement(db_session: AsyncSession):
    user = await crud.get_or_create_user(
        db_session,
        user_id=123456,
        username="testuser",
        full_name="Test User",
        is_premium=True
    )
    assert user.id == 123456
    assert user.is_premium is True
    assert user.is_agreed is False

    # Rozilik berish
    agreed = await crud.accept_agreement(db_session, 123456)
    assert agreed is True

    updated_user = await crud.get_user(db_session, 123456)
    assert updated_user.is_agreed is True
    assert updated_user.agreed_at is not None


@pytest.mark.asyncio
async def test_whitelist_management(db_session: AsyncSession):
    await crud.get_or_create_user(db_session, user_id=111, is_premium=True)

    # Chat qo'shish
    await crud.add_source_whitelist(db_session, user_id=111, chat_id=999, title="Bank Bot")

    # Tekshirish
    is_allowed = await crud.is_chat_whitelisted(db_session, user_id=111, chat_id=999)
    assert is_allowed is True

    is_random_allowed = await crud.is_chat_whitelisted(db_session, user_id=111, chat_id=888)
    assert is_random_allowed is False

    # O'chirish
    removed = await crud.remove_source_whitelist(db_session, user_id=111, chat_id=999)
    assert removed is True

    is_allowed_after = await crud.is_chat_whitelisted(db_session, user_id=111, chat_id=999)
    assert is_allowed_after is False


@pytest.mark.asyncio
async def test_transaction_lifecycle_and_security(db_session: AsyncSession):
    await crud.get_or_create_user(db_session, user_id=222, is_premium=True)

    # Tranzaksiya yaratish (xabar matni berilmaydi va saqlanmaydi)
    tx = await crud.create_transaction(
        db_session,
        user_id=222,
        business_message_id=55,
        source_chat_id=777,
        tx_type=TransactionType.INFLOW.value,
        amount=150000.0,
        currency="UZS",
        category="Click"
    )
    assert tx.id is not None
    assert tx.amount == 150000.0
    assert tx.status == TransactionStatus.ACTIVE.value
    assert not hasattr(tx, "text")
    assert not hasattr(tx, "raw_message")

    # Tahrirlash (edited_business_message)
    edited_tx = await crud.mark_transaction_edited(
        db_session,
        user_id=222,
        source_chat_id=777,
        business_message_id=55,
        tx_type=TransactionType.INFLOW.value,
        amount=200000.0,
        currency="UZS",
        category="Click"
    )
    assert edited_tx.status == TransactionStatus.EDITED.value
    assert edited_tx.amount == 200000.0

    # O'chirish (deleted_business_messages)
    deleted_count = await crud.mark_transaction_deleted(
        db_session,
        user_id=222,
        message_ids=[55]
    )
    assert deleted_count == 1

    fetched_tx = await crud.get_transaction_by_message(db_session, 222, 777, 55)
    assert fetched_tx.status == TransactionStatus.DELETED.value


@pytest.mark.asyncio
async def test_unparsed_counter(db_session: AsyncSession):
    await crud.get_or_create_user(db_session, user_id=333, is_premium=True)

    c1 = await crud.increment_unparsed_counter(db_session, user_id=333, source_chat_id=444)
    assert c1 == 1

    c2 = await crud.increment_unparsed_counter(db_session, user_id=333, source_chat_id=444)
    assert c2 == 2


@pytest.mark.asyncio
async def test_wipe_user_data_cascade(db_session: AsyncSession):
    """
    /ochirish buyrug'idan so'ng foydalanuvchiga tegishli barcha ma'lumotlar to'liq o'chib ketishini tekshirish.
    """
    await crud.get_or_create_user(db_session, user_id=444, is_premium=True)
    await crud.add_source_whitelist(db_session, user_id=444, chat_id=100)
    await crud.create_transaction(
        db_session,
        user_id=444,
        business_message_id=1,
        source_chat_id=100,
        tx_type=TransactionType.OUTFLOW.value,
        amount=50000.0
    )
    await crud.increment_unparsed_counter(db_session, user_id=444, source_chat_id=100)

    # To'liq o'chirish
    deleted = await crud.delete_all_user_data(db_session, 444)
    assert deleted is True

    # Foydalanuvchi va uning barcha yozuvlari yo'q bo'lganini tasdiqlash
    user = await crud.get_user(db_session, 444)
    assert user is None

    whitelists = await crud.get_user_whitelists(db_session, 444)
    assert len(whitelists) == 0
