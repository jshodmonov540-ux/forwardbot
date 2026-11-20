from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.base import async_session_factory
from db import crud
from core.logger import logger

router = Router(name="sources_router")


class AddSourceState(StatesGroup):
    waiting_for_chat_id = State()


class RenameSourceState(StatesGroup):
    waiting_for_new_title = State()


@router.message(Command("manbalar"))
@router.message(F.text.in_({"📋 Manbalar", "📋 Manbalar (Oq ro'yxat)"}))
async def cmd_sources(message: Message):
    user_id = message.from_user.id
    async with async_session_factory() as session:
        sources = await crud.get_user_whitelists(session, user_id)

    if not sources:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ ID orqali qo'shish", callback_data="add_source_manual")]
            ]
        )
        await message.answer(
            "📋 <b>Ruxsat etilgan manbalar (Whitelist) ro'yxati bo'sh!</b>\n\n"
            "Bot faqat siz ruxsat bergan chatlardan kelgan xabarlarni o'qiydi va yo'naltiradi.\n\n"
            "<b>Qanday qo'shish mumkin?</b>\n"
            "1️⃣ Bank yoki to'lov botidan kelgan istalgan xabarni shu yerga (botga) <b>Forward</b> qiling.\n"
            "2️⃣ Yoki pastdagi <i>ID orqali qo'shish</i> tugmasini bosing.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    text = "📋 <b>Siz tasdiqlagan manbalar (Whitelist):</b>\n\n"
    buttons = []
    for s in sources:
        title = s.title or f"Chat ID: {s.chat_id}"
        text += f"• <b>{title}</b> (<code>{s.chat_id}</code>)\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ Nomlash",
                callback_data=f"rename_source_{s.chat_id}"
            ),
            InlineKeyboardButton(
                text=f"❌ O'chirish",
                callback_data=f"del_source_{s.chat_id}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="➕ ID orqali qo'shish", callback_data="add_source_manual")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text += "\n<i>Yangi manba qo'shish uchun bank/bot xabarini shu yerga Forward qiling yoki ID orqali qo'shing.</i>"
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "menu_sources")
async def on_menu_sources(callback: CallbackQuery):
    await cmd_sources(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("del_source_"))
async def on_delete_source(callback: CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    async with async_session_factory() as session:
        await crud.remove_source_whitelist(session, user_id, chat_id)

    await callback.answer("Manba o'chirildi!")
    # Ro'yxatni yangilash
    async with async_session_factory() as session:
        sources = await crud.get_user_whitelists(session, user_id)

    if not sources:
        await callback.message.edit_text(
            "📋 <b>Barcha manbalar o'chirildi!</b>\n"
            "Yangi manba qo'shish uchun xabarni forward qiling.",
            parse_mode="HTML"
        )
        return

    text = "📋 <b>Siz tasdiqlagan manbalar (Whitelist):</b>\n\n"
    buttons = []
    for s in sources:
        title = s.title or f"Chat ID: {s.chat_id}"
        text += f"• <b>{title}</b> (<code>{s.chat_id}</code>)\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ Nomlash",
                callback_data=f"rename_source_{s.chat_id}"
            ),
            InlineKeyboardButton(
                text=f"❌ O'chirish",
                callback_data=f"del_source_{s.chat_id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ ID orqali qo'shish", callback_data="add_source_manual")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "add_source_manual")
async def on_add_source_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddSourceState.waiting_for_chat_id)
    await callback.message.answer(
        "✍️ <b>Chat ID yoki kanal/bot ID sini kiriting:</b>\n"
        "Masalan: <code>8718610541</code>\n\n"
        "<i>Xohlasangiz nom bilan birga yozishingiz mumkin:</i>\n"
        "<code>8718610541 Payme bot</code>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AddSourceState.waiting_for_chat_id)
async def process_manual_chat_id(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    try:
        chat_id = int(parts[0])
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Chat ID butun son bo'lishi kerak.\nMasalan: <code>8718610541</code> yoki <code>8718610541 Payme bot</code>")
        return

    custom_title = parts[1].strip() if len(parts) > 1 else None
    title = custom_title
    user_id = message.from_user.id

    # Avtomatik Telegram nomini aniqlash
    if not title:
        try:
            chat_obj = await message.bot.get_chat(chat_id)
            name_part = chat_obj.title or chat_obj.full_name
            if chat_obj.username:
                title = f"{name_part} (@{chat_obj.username})" if name_part else f"@{chat_obj.username}"
            else:
                title = name_part
        except Exception:
            pass

    if not title:
        try:
            from services.userbot_manager import userbot_manager
            client = userbot_manager.get_client(user_id)
            if client and client.is_connected():
                ent = await client.get_entity(chat_id)
                ent_title = getattr(ent, 'title', None)
                ent_name = getattr(ent, 'first_name', None)
                if getattr(ent, 'last_name', None):
                    ent_name = f"{ent_name} {ent.last_name}"
                ent_user = getattr(ent, 'username', None)
                name_part = ent_title or ent_name
                if name_part and ent_user:
                    title = f"{name_part} (@{ent_user})"
                elif name_part:
                    title = name_part
                elif ent_user:
                    title = f"@{ent_user}"
        except Exception:
            pass

    if not title:
        title = f"Chat {chat_id}"

    async with async_session_factory() as session:
        await crud.add_source_whitelist(session, user_id, chat_id, title=title)

    await state.clear()
    await message.answer(
        f"✅ <b>Manba muvaffaqiyatli qo'shildi!</b>\n\n"
        f"• Nomi: <b>{title}</b>\n"
        f"• Chat ID: <code>{chat_id}</code>\n\n"
        "Endi bu chatdan kelgan xabarlar avtomatik yo'naltiriladi.\n"
        "<i>(Nomini xohlagan vaqt /manbalar orqali o'zgartirishingiz mumkin)</i>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("rename_source_"))
async def on_rename_source(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split("_")[2])
    await state.set_state(RenameSourceState.waiting_for_new_title)
    await state.update_data(rename_chat_id=chat_id)
    await callback.message.answer(
        f"✍️ <code>{chat_id}</code> manbasi uchun yangi nom kiriting:\n"
        "Masalan: <i>Payme bot</i>, <i>Click to'lovlar</i>, <i>Jo'rabek</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(RenameSourceState.waiting_for_new_title)
async def process_rename_source(message: Message, state: FSMContext):
    new_title = message.text.strip()
    data = await state.get_data()
    chat_id = data.get("rename_chat_id")
    user_id = message.from_user.id
    await state.clear()

    if not chat_id:
        await message.answer("❌ Xatolik yuz berdi. Qaytadan /manbalar orqali urinib ko'ring.")
        return

    async with async_session_factory() as session:
        await crud.add_source_whitelist(session, user_id, chat_id, title=new_title)

    await message.answer(
        f"✅ <b>Manba nomi muvaffaqiyatli o'zgartirildi!</b>\n\n"
        f"• Yangi nom: <b>{new_title}</b>\n"
        f"• Chat ID: <code>{chat_id}</code>",
        parse_mode="HTML"
    )


# Forward qilingan xabarni aniqlash
@router.message(F.forward_origin | F.forward_from | F.forward_from_chat)
async def handle_forwarded_message(message: Message):
    # Forward ma'lumotlarini olish
    chat_id = None
    title = None

    if message.forward_origin:
        origin = message.forward_origin
        if origin.type == "chat" and hasattr(origin, "chat"):
            chat_id = origin.chat.id
            title = origin.chat.title
        elif origin.type == "user" and hasattr(origin, "sender_user"):
            chat_id = origin.sender_user.id
            title = origin.sender_user.full_name
        elif origin.type == "channel" and hasattr(origin, "chat"):
            chat_id = origin.chat.id
            title = origin.chat.title

    if not chat_id:
        if message.forward_from_chat:
            chat_id = message.forward_from_chat.id
            title = message.forward_from_chat.title
        elif message.forward_from:
            chat_id = message.forward_from.id
            title = message.forward_from.full_name

    if chat_id:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Manba sifatida saqlash",
                        callback_data=f"confirm_source_{chat_id}_{title or 'Chat'}"
                    )
                ]
            ]
        )
        await message.answer(
            f"📥 <b>Forward qilingan xabar aniqlandi:</b>\n\n"
            f"• Nomi: <b>{title or 'Noma`lum'}</b>\n"
            f"• Chat ID: <code>{chat_id}</code>\n\n"
            "Ushbu chatni ruxsat etilgan manbalar (Whitelist) safiga qo'shasizmi?",
            reply_markup=kb,
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("confirm_source_"))
async def on_confirm_source(callback: CallbackQuery):
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    title = "_".join(parts[3:])
    user_id = callback.from_user.id

    async with async_session_factory() as session:
        await crud.add_source_whitelist(session, user_id, chat_id, title=title)

    await callback.message.edit_text(
        f"✅ <b>Manba Whitelist'ga qo'shildi!</b>\n\n"
        f"• Nomi: <b>{title}</b>\n"
        f"• Chat ID: <code>{chat_id}</code>\n\n"
        "Endi ushbu chatdan kelgan tranzaksiyalar yo'naltiriladi.",
        parse_mode="HTML"
    )
    await callback.answer("Qo'shildi!")
