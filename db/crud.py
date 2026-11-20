from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import (
    DestinationType,
    InviteCode,
    SourceWhitelist,
    Transaction,
    TransactionStatus,
    TransactionType,
    UnparsedCounter,
    User,
    utc_now,
)


# ===================== USER CRUD =====================

async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    is_premium: bool = False,
) -> User:
    user = await get_user(session, user_id)
    if not user:
        user = User(
            id=user_id,
            username=username,
            full_name=full_name,
            is_premium=is_premium,
            destination_chat_id=user_id,  # Standart maqsad - foydalanuvchining shaxsiy chati
            destination_type=DestinationType.PRIVATE.value,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        changed = False
        if user.is_premium != is_premium:
            user.is_premium = is_premium
            changed = True
        if username and user.username != username:
            user.username = username
            changed = True
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            await session.commit()
            await session.refresh(user)
    return user


async def accept_agreement(session: AsyncSession, user_id: int) -> bool:
    user = await get_user(session, user_id)
    if user:
        user.is_agreed = True
        user.agreed_at = utc_now()
        await session.commit()
        return True
    return False


async def update_business_connection(
    session: AsyncSession,
    user_id: int,
    connection_id: Optional[str],
    is_enabled: bool,
) -> Optional[User]:
    user = await get_user(session, user_id)
    if user:
        user.business_connection_id = connection_id
        user.business_enabled = is_enabled
        await session.commit()
        await session.refresh(user)
    return user


async def set_destination(
    session: AsyncSession,
    user_id: int,
    destination_chat_id: int,
    destination_type: str = DestinationType.PRIVATE.value,
) -> bool:
    user = await get_user(session, user_id)
    if user:
        user.destination_chat_id = destination_chat_id
        user.destination_type = destination_type
        await session.commit()
        return True
    return False


async def set_paused_status(session: AsyncSession, user_id: int, is_paused: bool) -> bool:
    user = await get_user(session, user_id)
    if user:
        user.is_paused = is_paused
        await session.commit()
        return True
    return False


async def save_userbot_session(session: AsyncSession, user_id: int, session_string: str) -> bool:
    user = await get_user(session, user_id)
    if user:
        user.session_string = session_string
        user.is_userbot_active = True
        await session.commit()
        return True
    return False


async def deactivate_userbot(session: AsyncSession, user_id: int) -> bool:
    user = await get_user(session, user_id)
    if user:
        user.is_userbot_active = False
        user.session_string = None
        await session.commit()
        return True
    return False


async def get_active_userbots(session: AsyncSession) -> List[User]:
    stmt = select(User).where(User.is_userbot_active == True, User.session_string.isnot(None))
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def delete_all_user_data(session: AsyncSession, user_id: int) -> bool:
    """
    Foydalanuvchiga tegishli barcha ma'lumotlarni bazadan to'liq o'chiradi.
    Barcha jadvallar (transactions, sources, unparsed_counters, user) to'liq tozalanadi.
    """
    await session.execute(delete(Transaction).where(Transaction.user_id == user_id))
    await session.execute(delete(SourceWhitelist).where(SourceWhitelist.user_id == user_id))
    await session.execute(delete(UnparsedCounter).where(UnparsedCounter.user_id == user_id))
    stmt = delete(User).where(User.id == user_id)
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount > 0


# ===================== WHITELIST CRUD =====================

async def add_source_whitelist(
    session: AsyncSession,
    user_id: int,
    chat_id: int,
    title: Optional[str] = None,
) -> SourceWhitelist:
    stmt = select(SourceWhitelist).where(
        SourceWhitelist.user_id == user_id,
        SourceWhitelist.chat_id == chat_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        if title and existing.title != title:
            existing.title = title
            await session.commit()
            await session.refresh(existing)
        return existing

    new_source = SourceWhitelist(
        user_id=user_id,
        chat_id=chat_id,
        title=title,
    )
    session.add(new_source)
    await session.commit()
    await session.refresh(new_source)
    return new_source


async def remove_source_whitelist(session: AsyncSession, user_id: int, chat_id: int) -> bool:
    stmt = delete(SourceWhitelist).where(
        SourceWhitelist.user_id == user_id,
        SourceWhitelist.chat_id == chat_id,
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount > 0


async def get_user_whitelists(session: AsyncSession, user_id: int) -> List[SourceWhitelist]:
    stmt = select(SourceWhitelist).where(SourceWhitelist.user_id == user_id).order_by(SourceWhitelist.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def is_chat_whitelisted(session: AsyncSession, user_id: int, chat_id: int) -> bool:
    stmt = select(SourceWhitelist.id).where(
        SourceWhitelist.user_id == user_id,
        SourceWhitelist.chat_id == chat_id,
    ).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


# ===================== TRANSACTIONS CRUD =====================

async def create_transaction(
    session: AsyncSession,
    user_id: int,
    business_message_id: int,
    source_chat_id: int,
    tx_type: str,
    amount: float,
    currency: str = "UZS",
    category: Optional[str] = None,
    parsed_at: Optional[datetime] = None,
) -> Transaction:
    """
    Tranzaksiya ma'lumotlarini bazaga saqlash.
    DIQQAT: Xabarning asl matni saqlanmaydi!
    """
    tx = Transaction(
        user_id=user_id,
        business_message_id=business_message_id,
        source_chat_id=source_chat_id,
        tx_type=tx_type,
        amount=amount,
        currency=currency,
        category=category,
        status=TransactionStatus.ACTIVE.value,
        parsed_at=parsed_at or utc_now(),
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


async def get_transaction_by_message(
    session: AsyncSession,
    user_id: int,
    source_chat_id: int,
    business_message_id: int,
) -> Optional[Transaction]:
    stmt = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.source_chat_id == source_chat_id,
        Transaction.business_message_id == business_message_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def mark_transaction_edited(
    session: AsyncSession,
    user_id: int,
    source_chat_id: int,
    business_message_id: int,
    tx_type: str,
    amount: float,
    currency: str,
    category: Optional[str] = None,
) -> Optional[Transaction]:
    tx = await get_transaction_by_message(session, user_id, source_chat_id, business_message_id)
    if tx:
        tx.tx_type = tx_type
        tx.amount = amount
        tx.currency = currency
        tx.category = category
        tx.status = TransactionStatus.EDITED.value
        await session.commit()
        await session.refresh(tx)
    return tx


async def mark_transaction_deleted(
    session: AsyncSession,
    user_id: int,
    message_ids: List[int],
) -> int:
    stmt = (
        update(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.business_message_id.in_(message_ids),
        )
        .values(status=TransactionStatus.DELETED.value)
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount


# ===================== UNPARSED COUNTER =====================

async def increment_unparsed_counter(
    session: AsyncSession,
    user_id: int,
    source_chat_id: int,
) -> int:
    """
    Aniqlanmagan xabar kelganda hisoblagichni oshirish. Matn saqlanmaydi!
    """
    stmt = select(UnparsedCounter).where(
        UnparsedCounter.user_id == user_id,
        UnparsedCounter.source_chat_id == source_chat_id,
    )
    res = await session.execute(stmt)
    record = res.scalar_one_or_none()
    if record:
        record.count += 1
        record.last_seen_at = utc_now()
        await session.commit()
        return record.count
    else:
        new_record = UnparsedCounter(
            user_id=user_id,
            source_chat_id=source_chat_id,
            count=1,
            last_seen_at=utc_now(),
        )
        session.add(new_record)
        await session.commit()
        return 1


# ===================== HISOBOTLAR =====================

async def get_report_stats(
    session: AsyncSession,
    user_id: int,
    period: str = "day",  # day, week, month
) -> dict:
    now = datetime.now(timezone.utc)
    if period == "day":
        start_time = now - timedelta(days=1)
    elif period == "week":
        start_time = now - timedelta(days=7)
    elif period == "month":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(days=1)

    # Faqat ACTIVE yoki EDITED bo'lgan tranzaksiyalar (DELETED hisoblanmaydi)
    stmt = select(
        Transaction.tx_type,
        Transaction.currency,
        func.sum(Transaction.amount).label("total_amount"),
        func.count(Transaction.id).label("total_count"),
    ).where(
        Transaction.user_id == user_id,
        Transaction.status.in_([TransactionStatus.ACTIVE.value, TransactionStatus.EDITED.value]),
        Transaction.created_at >= start_time,
    ).group_by(Transaction.tx_type, Transaction.currency)

    result = await session.execute(stmt)
    rows = result.all()

    stats = {
        "period": period,
        "inflow": {},
        "outflow": {},
        "inflow_count": 0,
        "outflow_count": 0,
    }

    for tx_type, currency, total_amount, count in rows:
        if tx_type == TransactionType.INFLOW.value:
            stats["inflow"][currency] = float(total_amount or 0)
            stats["inflow_count"] += count
        else:
            stats["outflow"][currency] = float(total_amount or 0)
            stats["outflow_count"] += count

    # Aniqlanmagan xabarlar soni
    unparsed_stmt = select(func.sum(UnparsedCounter.count)).where(UnparsedCounter.user_id == user_id)
    unparsed_res = await session.execute(unparsed_stmt)
    stats["unparsed_count"] = unparsed_res.scalar() or 0

    return stats


# ===================== INVITE CODES & ADMIN =====================

async def check_invite_code(session: AsyncSession, code: str) -> Optional[InviteCode]:
    stmt = select(InviteCode).where(InviteCode.code == code, InviteCode.is_used == False)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def use_invite_code(session: AsyncSession, code: str, user_id: int) -> bool:
    invite = await check_invite_code(session, code)
    if invite:
        invite.is_used = True
        invite.used_by = user_id
        await session.commit()
        return True
    return False


async def create_invite_code(session: AsyncSession, code: str) -> InviteCode:
    invite = InviteCode(code=code)
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    return invite


async def get_admin_global_stats(session: AsyncSession) -> dict:
    total_users_stmt = select(func.count(User.id))
    active_business_stmt = select(func.count(User.id)).where(User.business_enabled == True)
    total_tx_stmt = select(func.count(Transaction.id))
    
    total_users = (await session.execute(total_users_stmt)).scalar() or 0
    active_business = (await session.execute(active_business_stmt)).scalar() or 0
    total_tx = (await session.execute(total_tx_stmt)).scalar() or 0

    return {
        "total_users": total_users,
        "active_business": active_business,
        "total_transactions": total_tx,
    }
