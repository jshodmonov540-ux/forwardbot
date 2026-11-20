from aiogram import F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.config import settings
from core.logger import logger
from db.base import async_session_factory
from db import crud

router = Router(name="start_router")


class InviteState(StatesGroup):
    waiting_for_invite_code = State()


AGREEMENT_TEXT = (
    "🔒 <b>Maxfiylik va Xavfsizlik shartlari (Privacy Policy)</b>\n\n"
    "Ushbu bot siz tanlagan botlar va chatlardan kelgan xabarlarni kanalingizga xavfsiz forward qilish uchun xizmat qiladi.\n\n"
    "✅ <b>Nimalar saqlanadi:</b>\n"
    "• Siz tasdiqlagan manba chatlar (Whitelist) va maqsad kanal identifikatori.\n"
    "• Avtomatik ishlash uchun zarur bo'lgan shifrlangan sessiya kaliti.\n\n"
    "❌ <b>Nimalar QAT'IYAN SAQLANMAYDI:</b>\n"
    "• Xabarlarning asl matnlari, rasmlar va fayllar bazada saqlanmaydi va logga yozilmaydi.\n"
    "• Whitelist'da bo'lmagan shaxsiy yozishmalaringiz o'qilmaydi va saqlanmaydi.\n"
    "• 2FA parollar bazada saqlanmaydi va kiritilishi bilan chatdan darhol o'chiriladi.\n\n"
    "🛡 <b>Kiberxavfsizlik kafolati (Hack holatida):</b>\n"
    "• Server buzilgan taqdirda ham, bazada xabarlar tarixi saqlanmagani uchun yozishmalaringiz sizib chiqmaydi.\n"
    "• Telegram Sozlamalar ➡️ Qurilmalar bo'limidan sessiyani istalgan paytda 1 ta tugma bilan bekor qilishingiz mumkin.\n\n"
    "🗑 <b>To'liq o'chirish:</b>\n"
    "• Istalgan vaqtda <code>/ochirish</code> orqali barcha ma'lumotlaringizni to'liq yo'q qilishingiz mumkin.\n\n"
    "Xizmatdan foydalanish uchun quyidagi tugmani bosib roziligingizni bildiring:"
)

INSTRUCTION_TEXT = (
    "🚀 <b>Telegram hisobingizni ulash yo'riqnomasi:</b>\n\n"
    "1️⃣ Pastdagi <b>🔗 Akkauntni ulash</b> tugmasini bosing (yoki <code>/ulash</code> buyrug'ini yuboring).\n"
    "2️⃣ Ekranda paydo bo'lgan <b>QR-kod</b>ni Telegram ilovangiz orqali skaner qiling:\n"
    "   <i>(Sozlamalar ➡️ Qurilmalar ➡️ Yangi qurilmani ulash)</i>\n"
    "3️⃣ Hisobingiz ulangach, xabarlarni yo'naltiruvchi chatlarni <b>/manbalar</b> bo'limida belgilang!\n\n"
    "⚡️ <i>Sizning maxfiyligingiz to'liq kafolatlangan. Istalgan vaqtda sessiyani bekor qilishingiz mumkin.</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    is_premium = bool(message.from_user.is_premium)

    async with async_session_factory() as session:
        user = await crud.get_or_create_user(
            session=session,
            user_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_premium=is_premium,
        )

    # 1. Invite code tekshiruvi (agar yoqilgan bo'lsa)
    if settings.INVITE_CODE_REQUIRED and not user.is_agreed:
        invite_arg = command.args
        if invite_arg:
            async with async_session_factory() as session:
                is_valid = await crud.use_invite_code(session, invite_arg.strip(), user_id)
                if not is_valid:
                    await message.answer("❌ Noto'g'ri yoki allaqachon ishlatilgan taklifnoma (invite) kodi!")
                    return
        else:
            await state.set_state(InviteState.waiting_for_invite_code)
            await message.answer(
                "🔑 <b>Taklifnoma kodi talab qilinadi</b>\n\n"
                "Iltimos, sizga berilgan taklifnoma (invite) kodini kiriting:",
                parse_mode="HTML"
            )
            return

    # 2. Agar hali rozilik bermagan bo'lsa - Maxfiylik va Xavfsizlik shartlari chiqadi
    if not user.is_agreed:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Shartlarga roziman", callback_data="agree_terms")],
                [InlineKeyboardButton(text="❌ Rad etish", callback_data="decline_terms")]
            ]
        )
        await message.answer(AGREEMENT_TEXT, reply_markup=kb, parse_mode="HTML")
        return

    # 4. Agar allaqachon rozi bo'lgan bo'lsa - asosiy holat paneli va bosh menyu
    from handlers.status import get_main_reply_kb, render_status_content

    # Reply keyboard menyusini o'rnatish
    await message.answer(
        f"Assalomu alaykum, <b>{message.from_user.first_name}</b>! 👋\n"
        "ForwardBot boshqaruv paneliga xush kelibsiz.",
        reply_markup=get_main_reply_kb(),
        parse_mode="HTML"
    )

    # Tizim holati va inline boshqaruv paneli
    text, kb = await render_status_content(message.bot, user_id)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(InviteState.waiting_for_invite_code)
async def process_invite_code(message: Message, state: FSMContext):
    code = message.text.strip()
    user_id = message.from_user.id
    async with async_session_factory() as session:
        is_valid = await crud.use_invite_code(session, code, user_id)
        if not is_valid:
            await message.answer("❌ Noto'g'ri yoki allaqachon ishlatilgan taklifnoma kodi! Qaytadan urinib ko'ring:")
            return

    await state.clear()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Shartlarga roziman", callback_data="agree_terms")],
            [InlineKeyboardButton(text="❌ Rad etish", callback_data="decline_terms")]
        ]
    )
    await message.answer(
        "✅ Taklifnoma kodi qabul qilindi!\n\n" + AGREEMENT_TEXT,
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "agree_terms")
async def on_agree_terms(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_factory() as session:
        await crud.accept_agreement(session, user_id)

    from handlers.status import get_main_reply_kb

    # Asosiy klaviaturani chiqarish
    await callback.message.answer(
        f"Assalomu alaykum, <b>{callback.from_user.first_name}</b>! 👋\n"
        "ForwardBot boshqaruv paneliga xush kelibsiz.",
        reply_markup=get_main_reply_kb(),
        parse_mode="HTML"
    )

    text = (
        "🎉 <b>Roziligingiz qabul qilindi va vaqti saqlab qo'yildi!</b>\n\n"
        + INSTRUCTION_TEXT
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Akkauntni ulash (QR-kod)", callback_data="start_userbot_qr")],
            [InlineKeyboardButton(text="📊 Tizim holati", callback_data="refresh_status")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer("Rozilik tasdiqlandi!")


@router.callback_query(F.data == "decline_terms")
async def on_decline_terms(callback: CallbackQuery):
    await callback.message.edit_text(
        "❌ <b>Siz shartlarni rad etdingiz.</b>\n\n"
        "Xizmatdan foydalanish uchun shartlarga rozilik bildirish talab etiladi. "
        "Fikringiz o'zgarsa, <code>/start</code> buyrug'ini bosing.",
        parse_mode="HTML"
    )
    await callback.answer()
