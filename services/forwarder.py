from datetime import datetime
from typing import Optional
from aiogram import Bot
from aiogram.types import Message
from db.models import TransactionType, TransactionStatus
from services.parser import ParsedTransaction
from core.logger import logger


def format_amount(amount: float, currency: str) -> str:
    # 150000 -> 150,000
    if amount.is_integer():
        formatted_val = f"{int(amount):,}".replace(",", " ")
    else:
        formatted_val = f"{amount:,.2f}".replace(",", " ")
    return f"{formatted_val} {currency}"


def build_transaction_message(
    parsed: ParsedTransaction,
    source_title: Optional[str] = None,
    source_chat_id: Optional[int] = None,
    status: str = TransactionStatus.ACTIVE.value,
) -> str:
    if parsed.tx_type == TransactionType.INFLOW:
        icon = "🟢"
        title = "KIRIM TRANZAKSIYASI"
        sign = "+"
    else:
        icon = "🔴"
        title = "CHIQIM TRANZAKSIYASI"
        sign = "-"

    if status == TransactionStatus.EDITED.value:
        status_badge = "\n⚠️ <i>(Ushbu xabar tahrirlangan)</i>"
    else:
        status_badge = ""

    src_display = source_title if source_title else f"Chat {source_chat_id}"
    vendor_display = f"├ 🏢 <b>Xizmat:</b> {parsed.vendor}\n" if parsed.vendor else ""
    date_str = parsed.parsed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if parsed.parsed_at else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    text = (
        f"{icon} <b>{title}</b>{status_badge}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"├ 💰 <b>Summa:</b> {sign}{format_amount(parsed.amount, parsed.currency)}\n"
        f"{vendor_display}"
        f"├ 📁 <b>Manba:</b> {src_display}\n"
        f"└ 🕒 <b>Vaqt:</b> {date_str}\n"
    )
    return text


def build_deleted_notification(source_title: Optional[str], count: int) -> str:
    src_display = source_title or "Manba chati"
    return (
        f"🗑 <b>XABARLAR O'CHIRILDI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📁 <b>Manba:</b> {src_display}\n"
        f"ℹ️ {count} ta tranzaksiya xabari manba chatdan o'chirildi."
    )


async def send_to_destination(
    bot: Bot,
    destination_chat_id: int,
    text: str,
) -> bool:
    """
    Formatlangan xabarni foydalanuvchi tanlagan maqsadga (shaxsiy chat, guruh yoki kanal) yuboradi.
    DIQQAT: Bot o'z nomidan yuboradi (Telegram Business orqali foydalanuvchi nomidan yozilmaydi).
    """
    try:
        await bot.send_message(
            chat_id=destination_chat_id,
            text=text,
            parse_mode="HTML"
        )
        return True
    except Exception as e:
        logger.error(f"Xabarni maqsad chatga yuborishda xatolik: {e}")
        return False


async def forward_message_directly(
    bot: Bot,
    destination_chat_id: int,
    message: Message,
) -> bool:
    """
    Xabarni asl holatida maqsad manzilga (kanal, guruh) to'g'ridan-to'g'ri forward qilish / nusxalash.
    Hech qanday hisob-kitob, o'zgartirish yoki filtrlarsiz to'liq asl holatida uzatadi.
    """
    # 1. Standart forward_message orqali uzatish
    try:
        await bot.forward_message(
            chat_id=destination_chat_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        logger.info(f"Xabar forward_message orqali yo'naltirildi: {message.chat.id} -> {destination_chat_id}")
        return True
    except Exception as e1:
        logger.debug(f"forward_message ishlamadi ({e1}), copy_message bilan urinib ko'ramiz")

    # 2. copy_message orqali uzatish
    try:
        await bot.copy_message(
            chat_id=destination_chat_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        logger.info(f"Xabar copy_message orqali yo'naltirildi: {message.chat.id} -> {destination_chat_id}")
        return True
    except Exception as e2:
        logger.debug(f"copy_message ishlamadi ({e2}), to'g'ridan-to'g'ri kontent yuboriladi")

    # 3. Kontent turi bo'yicha to'g'ridan-to'g'ri yuborish (Fallback)
    try:
        if message.text:
            await bot.send_message(
                chat_id=destination_chat_id,
                text=message.text,
                entities=message.entities,
            )
            return True
        elif message.photo:
            await bot.send_photo(
                chat_id=destination_chat_id,
                photo=message.photo[-1].file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
            )
            return True
        elif message.video:
            await bot.send_video(
                chat_id=destination_chat_id,
                video=message.video.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
            )
            return True
        elif message.document:
            await bot.send_document(
                chat_id=destination_chat_id,
                document=message.document.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
            )
            return True
        elif message.audio:
            await bot.send_audio(
                chat_id=destination_chat_id,
                audio=message.audio.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
            )
            return True
        elif message.voice:
            await bot.send_voice(
                chat_id=destination_chat_id,
                voice=message.voice.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
            )
            return True
        elif message.video_note:
            await bot.send_video_note(
                chat_id=destination_chat_id,
                video_note=message.video_note.file_id,
            )
            return True
        elif message.sticker:
            await bot.send_sticker(
                chat_id=destination_chat_id,
                sticker=message.sticker.file_id,
            )
            return True
        elif message.animation:
            await bot.send_animation(
                chat_id=destination_chat_id,
                animation=message.animation.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
            )
            return True
        elif message.contact:
            await bot.send_contact(
                chat_id=destination_chat_id,
                phone_number=message.contact.phone_number,
                first_name=message.contact.first_name,
                last_name=message.contact.last_name,
            )
            return True
        elif message.location:
            await bot.send_location(
                chat_id=destination_chat_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude,
            )
            return True
    except Exception as ex:
        logger.error(f"Xabarni to'g'ridan-to'g'ri yuborishda xatolik: {ex}")
        return False
    return False
