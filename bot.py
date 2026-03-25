import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Debug: log all incoming updates
    @dp.update.outer_middleware()
    async def log_updates(handler, event, data):
        try:
            logger.info("UPDATE: %s", event.model_dump_json(exclude_none=True)[:500])
        except Exception:
            logger.info("UPDATE: type=%s id=%s", event.event_type, event.update_id)
        return await handler(event, data)

    logger.info("Starting channel-guard-bot...")
    # Must include chat_member to receive join events
    await dp.start_polling(bot, allowed_updates=["chat_member", "message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
