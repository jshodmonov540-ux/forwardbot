import asyncio
import io
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
import qrcode
from telethon import TelegramClient
from telethon.errors import (
    AuthKeyUnregisteredError,
    PasswordHashInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from core.config import settings
from core.logger import logger
from db.base import async_session_factory
from db import crud
from services.userbot_manager import userbot_manager

router = Router(name="userbot_auth_router")


class UserbotAuthState(StatesGroup):
    waiting_for_2fa_password = State()


@router.message(Command("ulash", "login", "connect"))
@router.message(F.text.in_({"📱 Akkauntni ulash (QR)", "📱 Akkauntni ulash"}))
@router.callback_query(F.data.in_({"start_qr_login", "start_userbot_qr"}))
async def start_qr_login_handler(event: Message | CallbackQuery, state: FSMContext, bot: Bot):
    user_id = event.from_user.id

    # 1. Ulangan hisob borligini tekshirish (1 tadan ortiq ulab bo'lmasligi uchun)
    async with async_session_factory() as session:
        user = await crud.get_user(session, user_id)

    if user and user.is_userbot_active and user.session_string:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔌 Ha, eski hisobni uzish va yangisini ulash",
                        callback_data="confirm_reconnect_userbot"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data="cancel_qr_login"
                    )
                ]
            ]
        )
        warning_text = (
            "⚠️ <b>Sizda allaqachon ulangan hisob mavjud!</b>\n\n"
            "Tizimda bir vaqtning o'zida faqat <b>1 ta hisob</b> ulash mumkin.\n"
            "Yangi hisob ulash uchun avval eski hisobingiz uziladi.\n\n"
            "Eski hisobingizni uzib, yangisini ulamoqchimisiz?"
        )
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(warning_text, reply_markup=kb, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(warning_text, reply_markup=kb, parse_mode="HTML")
        return

    await execute_qr_login(event, state, bot)


@router.callback_query(F.data == "confirm_reconnect_userbot")
async def on_confirm_reconnect_userbot(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    # Eski hisobni to'xtatish va o'chirish
    await userbot_manager.stop_userbot(user_id)
    async with async_session_factory() as session:
        await crud.deactivate_userbot(session, user_id)

    await callback.answer("Eski hisob uzildi. Yangi QR-kod tayyorlanmoqda...")
    await execute_qr_login(callback, state, bot)


async def execute_qr_login(event: Message | CallbackQuery, state: FSMContext, bot: Bot):
    user_id = event.from_user.id

    # 1. API_ID va API_HASH tekshiruvi
    try:
        api_id, api_hash = userbot_manager.get_api_credentials()
    except ValueError as e:
        msg_text = (
            "⚠️ <b>Telegram API sozlamalari topilmadi!</b>\n\n"
            "QR-kod orqali ulanish uchun loyihaning <code>.env</code> faylida <b>API_ID</b> va <b>API_HASH</b> ko'rsatilishi shart.\n\n"
            "<i>(Buni <a href='https://my.telegram.org'>my.telegram.org</a> saytidan 1 daqiqada bepul olishingiz mumkin)</i>"
        )
        if isinstance(event, CallbackQuery):
            await event.message.answer(msg_text, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(msg_text, parse_mode="HTML")
        return

    # 2. Yangi Telethon client yaratamiz
    # Agar oldingi login jarayoni bo'lsa, to'xtatamiz
    old_client = userbot_manager.pending_logins.pop(user_id, None)
    if old_client:
        try:
            await old_client.disconnect()
        except Exception:
            pass

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    try:
        qr_login = await client.qr_login()
    except Exception as e:
        logger.error(f"QR login yaratishda xatolik: {e}")
        await client.disconnect()
        error_msg = f"❌ QR-kod yaratishda xatolik yuz berdi: {e}"
        if isinstance(event, CallbackQuery):
            await event.message.answer(error_msg)
            await event.answer()
        else:
            await event.answer(error_msg)
        return

    # 3. QR-kod rasmini xotirada yaratamiz
    qr_img = qrcode.make(qr_login.url)
    bio = io.BytesIO()
    qr_img.save(bio, format="PNG")
    bio.seek(0)
    photo_file = BufferedInputFile(bio.read(), filename="telegram_qr_login.png")

    caption = (
        "📷 <b>Ushbu QR-kodni Telegram ilovangiz orqali skanerlang:</b>\n\n"
        "1️⃣ Telegram ➡️ <b>Sozlamalar (Settings)</b>\n"
        "2️⃣ <b>Qurilmalar (Devices)</b> bo'limiga kiring\n"
        "3️⃣ <b>Qurilmani ulash (Link Device)</b> tugmasini bosing va kamerani shu QR-kodga qarating\n\n"
        "⏳ <i>Kutilmoqda (QR-kod 60 soniya davomida amal qiladi)...</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_qr_login")]
        ]
    )

    if isinstance(event, CallbackQuery):
        sent_msg = await event.message.answer_photo(photo=photo_file, caption=caption, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        sent_msg = await event.answer_photo(photo=photo_file, caption=caption, reply_markup=kb, parse_mode="HTML")

    userbot_manager.pending_logins[user_id] = client

    # 4. Orqa fonda QR-kod tasdiqlanishini kutish vazifasi
    asyncio.create_task(
        wait_for_qr_scan(
            user_id=user_id,
            client=client,
            qr_login=qr_login,
            sent_msg=sent_msg,
            state=state,
            bot=bot,
        )
    )


async def wait_for_qr_scan(
    user_id: int,
    client: TelegramClient,
    qr_login,
    sent_msg: Message,
    state: FSMContext,
    bot: Bot,
):
    """QR-kod skaner qilinishini kutuvchi vazifa"""
    try:
        # 60 soniya kutish
        await qr_login.wait(timeout=60)

        # Muvaffaqiyatli login!
        session_str = client.session.save()
        async with async_session_factory() as session:
            await crud.save_userbot_session(session, user_id, session_str)

        userbot_manager.pending_logins.pop(user_id, None)
        await userbot_manager.start_userbot(user_id, session_str)

        await sent_msg.reply(
            "🎉 <b>Akkauntingiz muvaffaqiyatli ulandi!</b>\n\n"
            "Endi siz ruxsat bergan botlar va chatlardan kelgan barcha xabarlar avtomatik ravishda kanalingizga forward qilinadi.",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} QR-kod orqali muvaffaqiyatli ulandi.")

    except SessionPasswordNeededError:
        # 2FA (Ikki bosqichli tekshiruv) yoqilgan!
        logger.info(f"User {user_id} uchun 2FA parol talab qilinmoqda.")
        await state.set_state(UserbotAuthState.waiting_for_2fa_password)
        cancel_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_qr_login")]
            ]
        )
        await sent_msg.reply(
            "🔐 <b>QR-kod tasdiqlandi, lekin hisobingizda Ikki bosqichli tekshiruv (2FA) yoqilgan!</b>\n\n"
            "Iltimos, Telegram 2-bosqichli parolingizni (Cloud Password) shu yerga yozib yuboring:\n\n"
            "🛡 <i>Xavfsizlik kafolati: Parolingiz yozishingiz bilan darhol chatdan o'chirib tashlanadi va bazada saqlanmaydi.</i>",
            reply_markup=cancel_kb,
            parse_mode="HTML"
        )

    except asyncio.TimeoutError:
        # Vaqt tugadi
        if userbot_manager.pending_logins.get(user_id) == client:
            userbot_manager.pending_logins.pop(user_id, None)
            try:
                await client.disconnect()
            except Exception:
                pass
            await sent_msg.reply(
                "⏳ <b>QR-kod muddati tugadi.</b>\n"
                "Qaytadan urinish uchun «📱 Akkauntni ulash» tugmasini bosing.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"QR login kutishda xatolik (user_id={user_id}): {e}")
        userbot_manager.pending_logins.pop(user_id, None)
        try:
            await client.disconnect()
        except Exception:
            pass


@router.message(UserbotAuthState.waiting_for_2fa_password)
async def process_2fa_password(message: Message, state: FSMContext):
    user_id = message.from_user.id
    password = message.text.strip()

    # Xavfsizlik: Foydalanuvchi yozgan parolni chatdan darhol o'chirib tashlaymiz!
    try:
        await message.delete()
    except Exception:
        pass

    client = userbot_manager.pending_logins.get(user_id)
    if not client:
        await state.clear()
        await message.answer("❌ Ulanish sessiyasi topilmadi yoki vaqti tugadi. Qaytadan /start bosing.")
        return

    try:
        if not client.is_connected():
            await client.connect()

        await client.sign_in(password=password)
        session_str = client.session.save()

        async with async_session_factory() as session:
            await crud.save_userbot_session(session, user_id, session_str)

        userbot_manager.pending_logins.pop(user_id, None)
        await userbot_manager.start_userbot(user_id, session_str)
        await state.clear()

        await message.answer(
            "🎉 <b>Ikki bosqichli parol (2FA) muvaffaqiyatli tasdiqlandi!</b>\n\n"
            "Akkauntingiz ulandi. Endi belgilangan botlardan kelgan barcha xabarlar avtomatik tarzda kanalingizga forward qilinadi.",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} 2FA orqali muvaffaqiyatli ulandi.")

    except PasswordHashInvalidError:
        cancel_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_qr_login")]
            ]
        )
        await message.answer(
            "❌ <b>Kiritilgan 2FA parol noto'g'ri!</b>\n\n"
            "Iltimos, parolni tekshirib qaytadan kiriting:",
            reply_markup=cancel_kb,
            parse_mode="HTML"
        )
    except AuthKeyUnregisteredError:
        userbot_manager.pending_logins.pop(user_id, None)
        await state.clear()
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📱 Qaytadan QR-kod olish", callback_data="start_qr_login")]
            ]
        )
        await message.answer(
            "⏳ <b>Ulanish sessiyasi muddati tugadi!</b>\n\n"
            "Telegram xavfsizlik talablariga ko'ra, QR-kod skanerdan so'ng 2FA parol juda tez (taxminan 30 soniya ichida) tasdiqlanishi kerak.\n"
            "Sessiya eskirgani sababli, iltimos yangi QR-kod oling va parolni darhol kiriting.",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"2FA parolni tekshirishda xatolik: {e}")
        await message.answer(f"❌ Xatolik yuz berdi: {e}\nQaytadan urinib ko'ring:")


@router.callback_query(F.data == "cancel_qr_login")
async def on_cancel_qr_login(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    client = userbot_manager.pending_logins.pop(user_id, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass
    await state.clear()
    await callback.message.delete()
    await callback.answer("Ulanish bekor qilindi.")


@router.callback_query(F.data == "disconnect_userbot")
async def on_disconnect_userbot(callback: CallbackQuery):
    user_id = callback.from_user.id
    await userbot_manager.stop_userbot(user_id)
    async with async_session_factory() as session:
        await crud.deactivate_userbot(session, user_id)

    await callback.message.edit_text(
        "🔌 <b>Akkaunt muvaffaqiyatli uzildi!</b>\n\n"
        "Sessiya o'chirildi. Xabarlar endi forward qilinmaydi.\n"
        "Qayta ulash uchun /start yoki «Akkauntni ulash» tugmasidan foydalaning.",
        parse_mode="HTML"
    )
    await callback.answer("Akkaunt uzildi.")
