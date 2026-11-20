from typing import Tuple
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from db.base import async_session_factory
from db import crud
from db.models import DestinationType
from services.forwarder import format_amount

router = Router(name="status_router")


def get_main_reply_kb() -> ReplyKeyboardMarkup:
    """Doimiy pastki menyu tugmalari"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📱 Akkauntni ulash (QR)"),
                KeyboardButton(text="📊 Hozirgi holat"),
            ],
            [
                KeyboardButton(text="📋 Manbalar"),
                KeyboardButton(text="🎯 Maqsad (Kanal)"),
            ],
            [
                KeyboardButton(text="⚙️ Sozlamalar"),
                KeyboardButton(text="ℹ️ Yordam"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_main_inline_kb() -> InlineKeyboardMarkup:
    """Bosh menyu inline tugmalari"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Akkauntni ulash (QR-kod)",
                    callback_data="start_qr_login"
                ),
                InlineKeyboardButton(
                    text="📊 Hozirgi holat",
                    callback_data="view_status"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Manbalar (Whitelist)",
                    callback_data="menu_sources"
                ),
                InlineKeyboardButton(
                    text="🎯 Maqsad (Kanal)",
                    callback_data="menu_destination"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Sozlamalar",
                    callback_data="menu_settings"
                ),
                InlineKeyboardButton(
                    text="ℹ️ Yo'riqnoma va Yordam",
                    callback_data="view_help"
                ),
            ],
        ]
    )


async def render_status_content(bot: Bot, user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    """Foydalanuvchining hozirgi holati va barcha ulanishlarini chiroyli ko'rsatish"""
    async with async_session_factory() as session:
        user = await crud.get_user(session, user_id)
        if not user:
            return "❌ Foydalanuvchi topilmadi. Qaytadan /start bosing.", InlineKeyboardMarkup(inline_keyboard=[])

        sources = await crud.get_user_whitelists(session, user_id)

    # 1. Userbot ulanishi (Botlardan va odamlardan xabar olish uchun)
    if user.is_userbot_active and user.session_string:
        userbot_status = "🟢 <b>Ulangan (Faol)</b>"
        userbot_btn = InlineKeyboardButton(text="🔌 Akkauntni uzish", callback_data="disconnect_userbot")
    else:
        userbot_status = "🔴 <b>Ulanmagan</b> <i>(Botlardan xabar olish uchun ulang)</i>"
        userbot_btn = InlineKeyboardButton(text="📱 Akkauntni ulash (QR-kod)", callback_data="start_qr_login")

    # 2. Maqsad chat (Tranzaksiyalar yuboriladigan joy)
    dest_id = user.destination_chat_id or user.id
    dest_type = user.destination_type or DestinationType.PRIVATE.value

    type_icons = {
        DestinationType.PRIVATE.value: "👤 Shaxsiy bot yozishmasi",
        DestinationType.GROUP.value: "👥 Guruh / Superguruh",
        DestinationType.CHANNEL.value: "📢 Kanal",
    }
    type_display = type_icons.get(dest_type, dest_type)

    # Chat nomini olishga urinib ko'ramiz
    chat_title = None
    if dest_id != user.id:
        try:
            chat_obj = await bot.get_chat(dest_id)
            chat_title = chat_obj.title or chat_obj.full_name
        except Exception:
            chat_title = None

    dest_name_display = f"<b>{chat_title}</b> " if chat_title else ""
    dest_display = f"{type_display}\n   └ ID: <code>{dest_id}</code> {dest_name_display}"

    # 3. Ulangan manbalar (Whitelist)
    if sources:
        sources_list = []
        for idx, s in enumerate(sources, 1):
            s_title = s.title or f"Chat {s.chat_id}"
            sources_list.append(f"   {idx}. <b>{s_title}</b> (<code>{s.chat_id}</code>)")
        sources_display = f"Jami: <b>{len(sources)} ta</b>\n" + "\n".join(sources_list)
    else:
        sources_display = "<i>Hozircha hech qanday manba qo'shilmagan!</i>\n   <i>(/manbalar bo'limidan qo'shishingiz mumkin)</i>"

    # 4. Bot ish holati (Pauza / Faol)
    if user.is_paused:
        bot_state = "⏸ <b>Vaqtincha to'xtatilgan (Pauzada)</b>"
        pause_btn_text = "▶️ Davom ettirish"
    else:
        bot_state = "🟢 <b>Faol (Xabarlar tinglanmoqda)</b>"
        pause_btn_text = "⏸ Pauza qilish"

    text = (
        "📊 <b>FORWARDBOT TIZIM HOLATI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 <b>Telegram Userbot:</b> {userbot_status}\n\n"
        f"🎯 <b>Maqsad (Qayerga yuboriladi):</b>\n   {dest_display}\n\n"
        f"📋 <b>Ulangan manbalar (Oq ro'yxat):</b>\n{sources_display}\n\n"
        f"⚡️ <b>Ish holati:</b> {bot_state}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Manbadan kelgan har qanday xabar (botlar va foydalanuvchilar) to'g'ridan-to'g'ri kanalga forward qilinadi.</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                userbot_btn,
            ],
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_status"),
                InlineKeyboardButton(text=pause_btn_text, callback_data="toggle_pause_status"),
            ],
            [
                InlineKeyboardButton(text="➕ Manba qo'shish", callback_data="add_source_manual"),
                InlineKeyboardButton(text="🎯 Maqsadni sozlash", callback_data="set_dest_custom"),
            ],
            [
                InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="show_main_menu"),
            ],
        ]
    )

    return text, kb


@router.message(Command("holat", "status"))
@router.message(F.text.in_({"📊 Hozirgi holat", "📊 Holat", "📊 Status"}))
async def cmd_status(message: Message, bot: Bot):
    user_id = message.from_user.id
    text, kb = await render_status_content(bot, user_id)
    await message.answer(
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "view_status")
async def on_view_status(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    text, kb = await render_status_content(bot, user_id)
    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "refresh_status")
async def on_refresh_status(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    text, kb = await render_status_content(bot, user_id)
    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception:
        # Matn o'zgarmagan bo'lsa xatolik bermaydi
        pass
    await callback.answer("Ma'lumotlar yangilandi! ✅")


@router.callback_query(F.data == "toggle_pause_status")
async def on_toggle_pause_status(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    async with async_session_factory() as session:
        user = await crud.get_user(session, user_id)
        if user:
            new_status = not user.is_paused
            await crud.set_paused_status(session, user_id, new_status)
            status_msg = "Pauzaga qo'yildi ⏸" if new_status else "Qayta ishga tushirildi ▶️"
            await callback.answer(status_msg)

    text, kb = await render_status_content(bot, user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "show_main_menu")
async def on_show_main_menu(callback: CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    text = (
        f"🏠 <b>Bosh menyu</b>\n\n"
        f"Bot: @{bot_info.username}\n"
        "Kerakli bo'limni tanlang:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_main_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
