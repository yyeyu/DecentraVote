from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from handlers import routers
import asyncio
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

bot = Bot(
    token=os.getenv("TOKEN"),
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

for router in routers:
    dp.include_router(router)

async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")