from aiogram import Bot, Router
from aiogram.types import BusinessConnection
from core.logger import logger
from db.base import async_session_factory
from db import crud

router = Router(name="business_connection_router")


@router.business_connection()
async def handle_business_connection_update(connection: BusinessConnection, bot: Bot):
    user_id = connection.user.id
    connection_id = connection.id
    is_enabled = connection.is_enabled

    logger.info(f"business_connection update: user_id={user_id}, enabled={is_enabled}")

    async with async_session_factory() as session:
        await crud.update_business_connection(
            session=session,
            user_id=user_id,
            connection_id=connection_id if is_enabled else None,
            is_enabled=is_enabled
        )

    if is_enabled:
        text = (
            "✅ <b>Telegram Business muvaffaqiyatli ulandi!</b>\n\n"
            f"🔗 <b>Ulanish ID:</b> <code>{connection_id}</code>\n"
            "Bot endi siz ruxsat bergan chatlardagi tranzaksiyalarni kuzatishga tayyor.\n\n"
            "Keyingi qadamlar:\n"
            "1️⃣ <code>/manbalar</code> - qaysi chatlardan xabar olinishini sozlang (Whitelist).\n"
            "2️⃣ <code>/maqsad</code> - tranzaksiyalar qayerga yo'naltirilishini tanlang (shaxsiy chat, guruh yoki kanal).\n"
            "3️⃣ <code>/hisobot</code> - kirim va chiqim hisobotlarini ko'ring."
        )
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ulanish xabarini yuborishda xatolik: {e}")
    else:
        text = (
            "⚠️ <b>Telegram Business ulanishi to'xtatildi yoki uzildi!</b>\n\n"
            "Bot hisobingizdan uzildi yoki Telegram Premium muddati yakunlandi. "
            "Tranzaksiya xabarlarini tinglash to'xtatildi.\n"
            "Qayta ulash uchun Telegram Sozlamalar -> Business -> Chatbots bo'limiga kiring."
        )
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ulanish uzilganlik xabarini yuborishda xatolik: {e}")
