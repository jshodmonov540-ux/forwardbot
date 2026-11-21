import asyncio
import io
from typing import Dict, Optional
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramRetryAfter

from core.config import settings
from core.logger import logger
from db.base import async_session_factory
from db import crud


class FastMessageQueue:
    """
    Xabarlarni Telegram limitlariga tushmasdan (Flood control), 
    tezkor (1-2 soniya ichida) va birorta ham xabar yo'qolmasligini kafolatlovchi asinxron navbat.
    """
    def __init__(self):
        self.queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

    def start(self):
        if not self._worker_task or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def put(self, send_fn, *args, **kwargs):
        self.start()
        await self.queue.put((send_fn, args, kwargs))

    async def _worker_loop(self):
        while True:
            send_fn, args, kwargs = await self.queue.get()
            try:
                for attempt in range(3):
                    try:
                        await send_fn(*args, **kwargs)
                        # Agar navbatda yana xabarlar bo'lsa, xavfsiz 0.3 soniya tanaffus
                        if not self.queue.empty():
                            await asyncio.sleep(0.3)
                        break
                    except TelegramRetryAfter as e:
                        logger.warning(f"Telegram FloodWait cheklovi: {e.retry_after} soniya kutilmoqda...")
                        await asyncio.sleep(e.retry_after + 0.5)
                    except Exception as ex:
                        logger.error(f"Kanalga yuborishda xatolik (urinish {attempt+1}/3): {ex}")
                        if attempt < 2:
                            await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"FastMessageQueue worker kutilmagan xatolik: {e}")
            finally:
                self.queue.task_done()


class UserbotManager:
    def __init__(self):
        self.clients: Dict[int, TelegramClient] = {}
        # 2FA kutayotgan vaqtinchalik clientlar: user_id -> client
        self.pending_logins: Dict[int, TelegramClient] = {}
        self.aiogram_bot: Optional[Bot] = None
        self.fast_queue = FastMessageQueue()

    def set_bot(self, bot: Bot):
        self.aiogram_bot = bot
        self.fast_queue.start()

    def get_api_credentials(self) -> tuple[int, str]:
        """API ID va API HASH ni olish"""
        api_id = settings.API_ID
        api_hash = settings.API_HASH
        if not api_id or not api_hash:
            raise ValueError(
                "API_ID yoki API_HASH .env faylida sozlanmagan! "
                "Iltimos, my.telegram.org dan olib, .env ga API_ID va API_HASH ni qo'shing."
            )
        return int(api_id), str(api_hash)

    async def start_userbot(self, user_id: int, session_string: str) -> bool:
        """Foydalanuvchi uchun Telethon clientni ishga tushirish va hodisalarni tinglash"""
        await self.stop_userbot(user_id)

        try:
            api_id, api_hash = self.get_api_credentials()
            client = TelegramClient(StringSession(session_string), api_id, api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                logger.warning(f"Userbot session yaroqsiz: user_id={user_id}")
                return False

            # Barcha dialoglarni xotiraga yuklash
            try:
                await client.get_dialogs(limit=50)
            except Exception as dlg_err:
                logger.warning(f"Dialoglarni yuklashda ogohlantirish: {dlg_err}")

            self._register_handlers(client, user_id)
            self.clients[user_id] = client
            logger.info(f"Userbot muvaffaqiyatli ishga tushdi: user_id={user_id}")
            return True
        except Exception as e:
            logger.error(f"Userbotni ishga tushirishda xatolik (user_id={user_id}): {e}")
            return False

    def _register_handlers(self, client: TelegramClient, user_id: int):
        """Xabarlarni tinglash va navbat orqali xavfsiz/tezkor forward qilish"""
        @client.on(events.NewMessage(incoming=True))
        async def incoming_message_handler(event: events.NewMessage.Event):
            try:
                sender_chat_id = event.chat_id

                async with async_session_factory() as session:
                    user = await crud.get_user(session, user_id)
                    if not user or user.is_paused or user.is_blocked:
                        return

                    # Faqat ruxsat berilgan (Whitelist) manbalardan kelgan xabarlar o'tadi
                    is_whitelisted = await crud.is_chat_whitelisted(session, user_id, sender_chat_id)
                    if not is_whitelisted:
                        return

                    dest_chat_id = user.destination_chat_id
                    if not dest_chat_id:
                        return

                logger.info(
                    f"Userbot xabarni qabul qildi: user={user_id}, "
                    f"source={sender_chat_id} -> dest={dest_chat_id}"
                )

                # Yuboruvchi ismini aniqlash
                try:
                    sender = await event.get_sender()
                except Exception:
                    sender = None

                sender_name = "Noma'lum"
                if sender:
                    if hasattr(sender, "title") and sender.title:
                        sender_name = sender.title
                    elif hasattr(sender, "first_name") and sender.first_name:
                        sender_name = sender.first_name
                        if getattr(sender, "last_name", None):
                            sender_name += f" {sender.last_name}"
                    elif hasattr(sender, "username") and sender.username:
                        sender_name = f"@{sender.username}"

                msg = event.message
                text = msg.text or ""
                header = f"<b>{sender_name}:</b>"
                full_text = f"{header}\n{text}" if text else header

                media_data = None
                media_type = None
                media_filename = None
                is_voice = False
                is_video = False

                if msg.media:
                    try:
                        bio = io.BytesIO()
                        await event.message.download_media(file=bio)
                        bio.seek(0)
                        media_data = bio.read()
                        if isinstance(msg.media, MessageMediaPhoto):
                            media_type = "photo"
                        elif isinstance(msg.media, MessageMediaDocument):
                            media_type = "document"
                            media_filename = getattr(msg.file, "name", None) or "document"
                            is_voice = bool(getattr(msg, "voice", False))
                            is_video = bool(getattr(msg, "video", False))
                    except Exception as med_err:
                        logger.warning(f"Media yuklab olishda ogohlantirish: {med_err}")

                # Xabarni navbatga uzatamiz (tezkor, birorta xabar yo'qolmasligi va flood bo'lmasligi uchun)
                await self.fast_queue.put(
                    self._send_payload_via_bot,
                    dest_chat_id,
                    full_text,
                    media_data,
                    media_type,
                    media_filename,
                    is_voice,
                    is_video,
                    sender_name,
                )

            except Exception as e:
                logger.error(f"Userbot xabarini yo'naltirishda kutilmagan xatolik: {e}")

    async def _send_payload_via_bot(
        self,
        dest_chat_id: int,
        full_text: str,
        media_data: Optional[bytes],
        media_type: Optional[str],
        media_filename: Optional[str],
        is_voice: bool,
        is_video: bool,
        sender_name: str,
    ) -> bool:
        """Kanalga xabarni Bot orqali yetkazish (FloodWait va xatoliklarni qayta urinish bilan)"""
        if not self.aiogram_bot:
            logger.error("Aiogram bot sozlanmagan, kanalga yuborib bo'lmadi.")
            return False

        if media_data:
            if media_type == "photo":
                input_file = BufferedInputFile(media_data, filename="photo.jpg")
                await self.aiogram_bot.send_photo(chat_id=dest_chat_id, photo=input_file, caption=full_text, parse_mode="HTML")
            elif media_type == "document":
                input_file = BufferedInputFile(media_data, filename=media_filename or "document")
                if is_voice:
                    await self.aiogram_bot.send_voice(chat_id=dest_chat_id, voice=input_file, caption=full_text, parse_mode="HTML")
                elif is_video:
                    await self.aiogram_bot.send_video(chat_id=dest_chat_id, video=input_file, caption=full_text, parse_mode="HTML")
                else:
                    await self.aiogram_bot.send_document(chat_id=dest_chat_id, document=input_file, caption=full_text, parse_mode="HTML")
            else:
                input_file = BufferedInputFile(media_data, filename="file")
                await self.aiogram_bot.send_document(chat_id=dest_chat_id, document=input_file, caption=full_text, parse_mode="HTML")
        elif full_text:
            await self.aiogram_bot.send_message(chat_id=dest_chat_id, text=full_text, parse_mode="HTML")

        logger.info(f"Xabar Bot orqali muvaffaqiyatli kanalga yetkazildi ({sender_name}): dest={dest_chat_id}")
        return True

    async def stop_userbot(self, user_id: int):
        """Userbotni to'xtatish"""
        client = self.clients.pop(user_id, None)
        if client:
            try:
                await client.disconnect()
                logger.info(f"Userbot to'xtatildi: user_id={user_id}")
            except Exception as e:
                logger.warning(f"Userbotni to'xtatishda ogohlantirish: {e}")

    async def init_all_active_userbots(self):
        """Bot ishga tushganda barcha faol userbotlarni qayta ulash"""
        try:
            async with async_session_factory() as session:
                active_users = await crud.get_active_userbots(session)
            
            logger.info(f"Faol userbotlar soni: {len(active_users)} ta")
            for user in active_users:
                if user.session_string:
                    await self.start_userbot(user.id, user.session_string)
        except Exception as e:
            logger.error(f"Userbotlarni yuklashda xatolik: {e}")

    async def is_userbot_running(self, user_id: int) -> bool:
        """Userbot hozir ulanib ishlayaptimi?"""
        client = self.clients.get(user_id)
        if client and client.is_connected():
            return await client.is_user_authorized()
        return False


userbot_manager = UserbotManager()
