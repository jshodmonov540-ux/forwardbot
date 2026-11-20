import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from core.config import settings
from core.logger import logger
from db.base import engine, Base
from handlers import (
    admin,
    business_connection,
    business_message,
    destination,
    reports,
    settings as settings_handler,
    sources,
    start,
    status,
    userbot_auth,
)

ALLOWED_UPDATES = [
    "message",
    "callback_query",
    "business_connection",
    "business_message",
    "edited_business_message",
    "deleted_business_messages",
]


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database jadvallari tekshirildi va tayyorlandi.")


def create_dispatcher() -> Dispatcher:
    storage = MemoryStorage()
    if settings.REDIS_URL:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            storage = RedisStorage.from_url(settings.REDIS_URL)
            logger.info("Redis FSM storage ulandi.")
        except ImportError:
            logger.warning("redis-py o'rnatilmagan, MemoryStorage ishlatiladi.")
        except Exception as e:
            logger.warning(f"Redis ulanmadi ({e}), MemoryStorage ishlatiladi.")

    dp = Dispatcher(storage=storage)

    # Routerlarni tartib bilan ulash
    dp.include_router(start.router)
    dp.include_router(userbot_auth.router)
    dp.include_router(status.router)
    dp.include_router(business_connection.router)
    dp.include_router(business_message.router)
    dp.include_router(sources.router)
    dp.include_router(destination.router)
    dp.include_router(reports.router)
    dp.include_router(settings_handler.router)
    dp.include_router(admin.router)

    return dp


async def main():
    logger.info("ForwardBot ishga tushirilmoqda...")

    await init_models()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    from services.userbot_manager import userbot_manager
    userbot_manager.set_bot(bot)
    dp = create_dispatcher()

    if settings.USE_WEBHOOK and settings.WEBHOOK_URL:
        from aiohttp import web
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

        webhook_url = f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}"
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=ALLOWED_UPDATES,
            secret_token=settings.WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        logger.info(f"Webhook sozlandi: {webhook_url}")

        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.WEBHOOK_SECRET,
        )
        webhook_requests_handler.register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, settings.WEBHOOK_HOST, settings.WEBHOOK_PORT)
        await site.start()
        logger.info(f"Webhook server ishga tushdi: {settings.WEBHOOK_HOST}:{settings.WEBHOOK_PORT}")
        
        # Keep running
        await asyncio.Event().wait()
    else:
        # Polling rejimi
        await bot.delete_webhook(drop_pending_updates=True)
        from services.userbot_manager import userbot_manager
        await userbot_manager.init_all_active_userbots()

        from aiogram.types import BotCommand
        await bot.set_my_commands([
            BotCommand(command="start", description="Bosh menyu"),
            BotCommand(command="ulash", description="Akkauntni ulash (QR-kod)"),
            BotCommand(command="holat", description="Tizim holati va ulanishlar"),
            BotCommand(command="manbalar", description="Ruxsat berilgan manbalar"),
            BotCommand(command="maqsad", description="Yo'naltirish manzili"),
            BotCommand(command="pauza", description="Tinglashni to'xtatish"),
            BotCommand(command="davom", description="Qayta ishga tushirish"),
            BotCommand(command="sozlamalar", description="Sozlamalar"),
            BotCommand(command="maxfiylik", description="Maxfiylik siyosati"),
            BotCommand(command="yordam", description="Qo'llanma va yordam"),
        ])
        logger.info("Bot buyruqlari menyusi sozlandi.")
        logger.info("Polling rejimi boshlandi. allowed_updates tinglanmoqda...")
        await dp.start_polling(
            bot,
            allowed_updates=ALLOWED_UPDATES,
            close_bot_session=True,
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
