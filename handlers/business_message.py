from typing import List, Optional
from aiogram import Bot, Router
from aiogram.types import BusinessMessagesDeleted, Message
from core.logger import logger
from db.base import async_session_factory
from db import crud
from services.forwarder import forward_message_directly

router = Router(name="business_message_router")


@router.business_message()
async def handle_business_message(message: Message, bot: Bot):
    """
    Foydalanuvchi ulanishi orqali kelgan yangi biznes xabari.
    Faqat ruxsat berilgan (Whitelist) chatlardan kelgan xabarlarni
    to'g'ridan-to'g'ri kanal yoki guruhga asl holatida forward qiladi.
    """
    conn_id = message.business_connection_id
    if not conn_id:
        return

    source_chat_id = message.chat.id
    source_title = message.chat.full_name or message.chat.title
    msg_preview = message.text or message.caption or f"Media[{message.content_type}]"

    logger.info(
        f"Yangi xabar keldi: conn_id={conn_id}, "
        f"source_chat_id={source_chat_id} ({source_title}), "
        f"preview='{msg_preview[:50]}'"
    )

    async with async_session_factory() as session:
        from sqlalchemy import select
        from db.models import User
        stmt = select(User).where(User.business_connection_id == conn_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            logger.warning(f"Connection ID {conn_id} ga tegishli foydalanuvchi topilmadi.")
            return

        # Pauzada bo'lsa yoki bloklangan bo'lsa
        if user.is_paused or user.is_blocked or not user.business_enabled:
            logger.info(f"Foydalanuvchi {user.id} pauzada yoki ulanish o'chirilgan.")
            return

        # 2. Whitelist tekshiruvi (Faqat ruxsat berilgan chatlar yo'naltiriladi)
        is_allowed = await crud.is_chat_whitelisted(session, user.id, source_chat_id)
        if not is_allowed:
            logger.info(f"Chat {source_chat_id} whitelist'da yo'q, xabar o'tkazib yuborildi.")
            return

    # 3. Xabarni to'g'ridan-to'g'ri maqsad kanal/guruhga forward qilish
    dest_chat_id = user.destination_chat_id or user.id
    success = await forward_message_directly(
        bot=bot,
        destination_chat_id=dest_chat_id,
        message=message,
    )
    if success:
        logger.info(f"Xabar muvaffaqiyatli forward qilindi: {source_chat_id} -> {dest_chat_id}")
    else:
        logger.error(f"Xabarni forward qilishda xatolik: {source_chat_id} -> {dest_chat_id}")


@router.edited_business_message()
async def handle_edited_business_message(message: Message, bot: Bot):
    """
    Tahrirlangan xabar: tranzaksiya qayta tekshiriladi va yangilanadi yoki belgilanadi.
    """
    conn_id = message.business_connection_id
    if not conn_id:
        return

    source_chat_id = message.chat.id
    source_title = message.chat.full_name or message.chat.title

    async with async_session_factory() as session:
        from sqlalchemy import select
        from db.models import User
        stmt = select(User).where(User.business_connection_id == conn_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user or user.is_paused or user.is_blocked:
            return

        is_allowed = await crud.is_chat_whitelisted(session, user.id, source_chat_id)
        if not is_allowed:
            return

        msg_text = message.text or message.caption or ""
        parsed = parser.parse(msg_text)

        if parsed.is_parsed and parsed.amount > 0:
            updated_tx = await crud.mark_transaction_edited(
                session=session,
                user_id=user.id,
                source_chat_id=source_chat_id,
                business_message_id=message.message_id,
                tx_type=parsed.tx_type.value,
                amount=parsed.amount,
                currency=parsed.currency,
                category=parsed.vendor,
            )

            if updated_tx:
                dest_chat_id = user.destination_chat_id or user.id
                formatted_text = build_transaction_message(
                    parsed=parsed,
                    source_title=source_title,
                    source_chat_id=source_chat_id,
                    status=TransactionStatus.EDITED.value,
                )
                await send_to_destination(
                    bot=bot,
                    destination_chat_id=dest_chat_id,
                    text=formatted_text,
                )
                logger.info(f"Transaction edited notification sent for user_id={user.id}")


@router.deleted_business_messages()
async def handle_deleted_business_messages(event: BusinessMessagesDeleted, bot: Bot):
    """
    O'chirilgan xabarlar: tranzaksiya holati DELETED deb belgilanadi, ma'lumot saqlanmaydi.
    """
    conn_id = event.business_connection_id
    deleted_ids: List[int] = event.message_ids
    source_chat_id = event.chat.id
    source_title = event.chat.full_name or event.chat.title

    async with async_session_factory() as session:
        from sqlalchemy import select
        from db.models import User
        stmt = select(User).where(User.business_connection_id == conn_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            return

        affected_rows = await crud.mark_transaction_deleted(
            session=session,
            user_id=user.id,
            message_ids=deleted_ids,
        )

    if affected_rows > 0:
        dest_chat_id = user.destination_chat_id or user.id
        notify_text = build_deleted_notification(source_title, affected_rows)
        await send_to_destination(bot=bot, destination_chat_id=dest_chat_id, text=notify_text)
        logger.info(f"Marked {affected_rows} transactions as deleted for user_id={user.id}")
