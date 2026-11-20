from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from db.base import async_session_factory
from db import crud
from core.logger import logger

router = Router(name="settings_router")


@router.message(Command("pauza"))
async def cmd_pause(message: Message):
    user_id = message.from_user.id
    async with async_session_factory() as session:
        await crud.set_paused_status(session, user_id, is_paused=True)

    await message.answer(
        "⏸ <b>Tinglash vaqtincha to'xtatildi!</b>\n\n"
        "Yangi tranzaksiyalar siz uni qayta yoqguningizcha yo'naltirilmaydi.\n"
        "Qayta faollashtirish uchun <code>/davom</code> buyrug'ini yuboring.",
        parse_mode="HTML"
    )


@router.message(Command("davom"))
async def cmd_resume(message: Message):
    user_id = message.from_user.id
    async with async_session_factory() as session:
        await crud.set_paused_status(session, user_id, is_paused=False)

    await message.answer(
        "▶️ <b>Xizmat muvaffaqiyatli qayta ishga tushirildi!</b>\n\n"
        "Ruxsat berilgan chatlardan kelgan yangi tranzaksiyalar avtomatik tarzda yo'naltiriladi.",
        parse_mode="HTML"
    )


@router.message(Command("ochirish"))
async def cmd_delete_data(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Ha, barcha ma'lumotlarni o'chirish",
                    callback_data="confirm_wipe_user_data"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_wipe_user_data"
                )
            ]
        ]
    )
    await message.answer(
        "⚠️ <b>DIQQAT! Hisob va barcha ma'lumotlarni o'chirish</b>\n\n"
        "Ushbu amal hisobingizga tegishli barcha ma'lumotlarni:\n"
        "• Barcha ruxsat etilgan manbalarni (Whitelist),\n"
        "• Barcha saqlangan tranzaksiya statistikasini,\n"
        "• Hisob qaydnomangiz va sozlamalaringizni\n"
        "bazadan <b>to'liq va qaytarib bo'lmas darajada</b> o'chirib tashlaydi!\n\n"
        "Rostdan ham barchasini o'chirmoqchimisiz?",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_wipe_user_data")
async def on_confirm_wipe(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_factory() as session:
        await crud.delete_all_user_data(session, user_id)

    logger.info(f"All data wiped for user_id={user_id}")
    await callback.message.edit_text(
        "✅ <b>Barcha ma'lumotlaringiz bazadan to'liq o'chirildi!</b>\n\n"
        "Sizga tegishli hech qanday yozuv qolmadi. Telegram Sozlamalar -> Business -> Chatbots bo'limidan botni o'chirib qo'yishingiz mumkin.\n"
        "Qaytadan foydalanish uchun <code>/start</code> buyrug'ini bosing.",
        parse_mode="HTML"
    )
    await callback.answer("Ma'lumotlar o'chirildi!")


@router.callback_query(F.data == "cancel_wipe_user_data")
async def on_cancel_wipe(callback: CallbackQuery):
    await callback.message.edit_text(
        "Amal bekor qilindi. Ma'lumotlaringiz xavfsiz holatda saqlanmoqda.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("maxfiylik"))
async def cmd_privacy(message: Message):
    from handlers.start import AGREEMENT_TEXT
    await message.answer(AGREEMENT_TEXT, parse_mode="HTML")


@router.message(Command("yordam"))
@router.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: Message):
    text = (
        "ℹ️ <b>Mavjud buyruqlar va xizmat qo'llanmasi:</b>\n\n"
        "• <code>/holat</code> - Tizim holati va hozirda ulangan xizmatlar (Status).\n"
        "• <code>/manbalar</code> - Ruxsat berilgan manbalar (Whitelist) ro'yxati va ularni boshqarish.\n"
        "• <code>/maqsad</code> - Tranzaksiyalar yuboriladigan manzil (shaxsiy chat, guruh yoki kanal).\n"
        "• <code>/hisobot</code> - Kirim va chiqimlar bo'yicha kunlik, haftalik va oylik hisobot.\n"
        "• <code>/pauza</code> - Tranzaksiyalarni tinglashni vaqtincha to'xtatish.\n"
        "• <code>/davom</code> - Tinglashni qayta davom ettirish.\n"
        "• <code>/ochirish</code> - Barcha ma'lumotlarni bazadan to'liq tozalash.\n"
        "• <code>/yordam</code> - Ushbu ma'lumotnomani ko'rsatish.\n\n"
        "🔒 <b>Xavfsizlik:</b> Bot xabarlarning asl matnini va shaxsiy suhbatlarni saqlamaydi va logga yozmaydi."
    )
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "view_help")
async def on_view_help(callback: CallbackQuery):
    await cmd_help(callback.message)
    await callback.answer()


@router.message(Command("sozlamalar"))
@router.message(F.text == "⚙️ Sozlamalar")
@router.callback_query(F.data == "menu_settings")
async def cmd_settings(event: Message | CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏸ Pauza qilish", callback_data="settings_pause"),
                InlineKeyboardButton(text="▶️ Davom ettirish", callback_data="settings_resume"),
            ],
            [
                InlineKeyboardButton(text="🗑 Barcha ma'lumotlarni o'chirish", callback_data="confirm_wipe_user_data"),
            ],
            [
                InlineKeyboardButton(text="📊 Tizim holatiga qaytish", callback_data="view_status"),
            ]
        ]
    )
    text = (
        "⚙️ <b>Sozlamalar bo'limi:</b>\n\n"
        "• <b>Pauza / Davom ettirish:</b> Tranzaksiyalarni qabul qilishni vaqtincha to'xtatish yoki qayta yoqish.\n"
        "• <b>Ma'lumotlarni o'chirish:</b> Bazadagi barcha yozuvlaringizni to'liq tozalash."
    )
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "settings_pause")
async def on_settings_pause(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_factory() as session:
        await crud.set_paused_status(session, user_id, is_paused=True)
    await callback.answer("Tinglash vaqtincha to'xtatildi! ⏸")
    await cmd_settings(callback)


@router.callback_query(F.data == "settings_resume")
async def on_settings_resume(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_factory() as session:
        await crud.set_paused_status(session, user_id, is_paused=False)
    await callback.answer("Xizmat qayta ishga tushirildi! ▶️")
    await cmd_settings(callback)
