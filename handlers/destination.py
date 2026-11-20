from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.base import async_session_factory
from db.models import DestinationType
from db import crud
from core.logger import logger

router = Router(name="destination_router")


class DestinationState(StatesGroup):
    waiting_for_chat_id = State()


@router.message(Command("maqsad"))
@router.message(F.text.in_({"🎯 Maqsad (Kanal)", "🎯 Maqsad"}))
async def cmd_destination(message: Message):
    user_id = message.from_user.id
    async with async_session_factory() as session:
        user = await crud.get_user(session, user_id)

    dest_chat = user.destination_chat_id if user else user_id
    dest_type = user.destination_type if user else DestinationType.PRIVATE.value

    type_labels = {
        DestinationType.PRIVATE.value: "👤 Shaxsiy chat (Bot yozishmasi)",
        DestinationType.GROUP.value: "👥 Guruh / Superguruh",
        DestinationType.CHANNEL.value: "📢 Kanal",
    }
    current_label = type_labels.get(dest_type, dest_type)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Shaxsiy chatga o'tkazish",
                    callback_data="set_dest_private"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Guruh yoki 📢 Kanal tanlash",
                    callback_data="set_dest_custom"
                )
            ]
        ]
    )

    await message.answer(
        f"🎯 <b>Tranzaksiyalarni yo'naltirish manzili:</b>\n\n"
        f"• Hozirgi maqsad turi: <b>{current_label}</b>\n"
        f"• Chat ID: <code>{dest_chat}</code>\n\n"
        "Barcha yangi tranzaksiyalar ushbu manzilga yuboriladi.",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "menu_destination")
async def on_menu_destination(callback: CallbackQuery):
    await cmd_destination(callback.message)
    await callback.answer()


@router.callback_query(F.data == "set_dest_private")
async def on_set_dest_private(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_factory() as session:
        await crud.set_destination(session, user_id, user_id, DestinationType.PRIVATE.value)

    await callback.message.edit_text(
        "✅ <b>Maqsad o'zgartirildi:</b>\n"
        "Tranzaksiyalar endi o'zingizning shaxsiy botingizga yuboriladi.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_dest_custom")
async def on_set_dest_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DestinationState.waiting_for_chat_id)
    await callback.message.answer(
        "⚙️ <b>Guruh yoki Kanalni ulash tartibi:</b>\n\n"
        "1️⃣ Botni o'zingizning guruhingiz yoki kanalingizga a'zo qilib qo'shing.\n"
        "2️⃣ Botga <b>xabar yuborish (va adminlik)</b> ruxsatini bering.\n"
        "3️⃣ Guruh yoki kanalning <b>Chat ID</b> raqamini shu yerga yuboring (masalan: <code>-1001234567890</code>).\n\n"
        "<i>Chat ID ni yuborishni kutyapman:</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DestinationState.waiting_for_chat_id)
async def process_custom_dest_chat_id(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    try:
        chat_id = int(text)
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Chat ID faqat sonlardan iborat bo'lishi kerak (masalan <code>-100...</code>).")
        return

    # Bot a'zoligi va ruxsatlarini tekshirish
    try:
        chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
        if chat_member.status in ["kicked", "left"]:
            await message.answer(
                "❌ <b>Bot ushbu chatda yo'q yoki chiqarib yuborilgan!</b>\n\n"
                "Iltimos, avval botni ushbu guruh/kanalga qo'shing va qaytadan ID yuboring.",
                parse_mode="HTML"
            )
            return

        chat_info = await bot.get_chat(chat_id)
        dest_type = DestinationType.CHANNEL.value if chat_info.type == "channel" else DestinationType.GROUP.value

    except Exception as e:
        logger.warning(f"Chatga a'zolikni tekshirishda xatolik: {e}")
        await message.answer(
            "❌ <b>Chat tekshiruvdan o'tmadi!</b>\n"
            "Bot ushbu chatni ko'ra olmadi. Bot guruhga/kanalga qo'shilganini va to'g'ri ID kiritganingizni tekshiring.",
            parse_mode="HTML"
        )
        return

    user_id = message.from_user.id
    async with async_session_factory() as session:
        await crud.set_destination(session, user_id, chat_id, dest_type)

    await state.clear()
    await message.answer(
        f"✅ <b>Maqsad muvaffaqiyatli belgilandi!</b>\n\n"
        f"• Chat: <b>{chat_info.title}</b>\n"
        f"• ID: <code>{chat_id}</code>\n"
        f"• Turi: <b>{dest_type}</b>\n\n"
        "Barcha yangi tranzaksiyalar endi ushbu manzilga yo'naltiriladi.",
        parse_mode="HTML"
    )
