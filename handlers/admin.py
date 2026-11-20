import secrets
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from core.config import settings
from db.base import async_session_factory
from db import crud
from db.models import User
from sqlalchemy import select

router = Router(name="admin_router")


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = (
        "👑 <b>Admin Boshqaruv Paneli</b>\n\n"
        "Mavjud admin buyruqlari:\n"
        "• <code>/create_invite [kod]</code> - Yangi invite-kod yaratish (agar kod yozilmasa, avtomatik yaratiladi).\n"
        "• <code>/admin_stats</code> - Tizimning umumiy statistikasi (shaxsiy ma'lumotlarsiz).\n"
        "• <code>/block &lt;user_id&gt;</code> - Foydalanuvchini bloklash.\n"
        "• <code>/unblock &lt;user_id&gt;</code> - Blokdan chiqarish."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("create_invite"))
async def cmd_create_invite(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return

    code = command.args.strip() if command.args else secrets.token_urlsafe(8).upper()

    async with async_session_factory() as session:
        invite = await crud.create_invite_code(session, code)

    bot_info = await message.bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={invite.code}"
    await message.answer(
        f"✅ <b>Yangi Invite-kod yaratildi:</b>\n\n"
        f"🔑 Kod: <code>{invite.code}</code>\n"
        f"🔗 Havola: {invite_link}",
        parse_mode="HTML"
    )


@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    async with async_session_factory() as session:
        stats = await crud.get_admin_global_stats(session)

    text = (
        "📊 <b>Umumiy Tizim Statistikasi (Shaxsiy ma'lumotsiz):</b>\n\n"
        f"• Jami ro'yxatdan o'tganlar: <b>{stats['total_users']}</b> nafar\n"
        f"• Faol ulangan biznes hisoblar: <b>{stats['active_business']}</b> ta\n"
        f"• Jami qayta ishlangan tranzaksiyalar: <b>{stats['total_transactions']}</b> ta\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("block"))
async def cmd_block_user(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id) or not command.args:
        return

    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("User ID noto'g'ri!")
        return

    async with async_session_factory() as session:
        stmt = select(User).where(User.id == target_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if user:
            user.is_blocked = True
            await session.commit()
            await message.answer(f"User <code>{target_id}</code> bloklandi.")
        else:
            await message.answer("Foydalanuvchi topilmadi.")


@router.message(Command("unblock"))
async def cmd_unblock_user(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id) or not command.args:
        return

    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("User ID noto'g'ri!")
        return

    async with async_session_factory() as session:
        stmt = select(User).where(User.id == target_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if user:
            user.is_blocked = False
            await session.commit()
            await message.answer(f"User <code>{target_id}</code> blokdan chiqarildi.")
        else:
            await message.answer("Foydalanuvchi topilmadi.")
