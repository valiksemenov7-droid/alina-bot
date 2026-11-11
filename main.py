import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import config
import db
import handlers_admin
import handlers_user
import seed


async def health_server():
    """Tiny HTTP endpoint so platforms that require an open port (Render web service) keep the app alive."""
    from aiohttp import web

    async def ok(_):
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", ok)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.PORT).start()


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set")
    if not config.OWNER_ID:
        raise SystemExit("OWNER_ID is not set (Telegram ID of the studio owner — send /id to @userinfobot or to this bot)")

    db.init()
    seed.run()
    db.add_admin(config.OWNER_ID, "owner", config.OWNER_ID)

    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(handlers_admin.router)   # admin first: its FSM inputs must win over client fallbacks
    dp.include_router(handlers_user.router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Start / Inicio / Начало"),
        BotCommand(command="menu", description="Menu / Menú / Меню"),
        BotCommand(command="cancel", description="Cancel / Cancelar / Отмена"),
    ])
    if config.PORT:
        await health_server()
    await bot.delete_webhook(drop_pending_updates=False)
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
