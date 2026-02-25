from aiogram import Bot, Dispatcher

from .config import AppConfig
from .constants import BASE_DIR
from .context import set_app_config
from .handlers import include_routers


async def run() -> None:
    app_config = AppConfig.load(BASE_DIR / "config.json", BASE_DIR / ".env")
    set_app_config(app_config)
    bot = Bot(token=app_config.bot_token)
    dp = Dispatcher()
    include_routers(dp)
    await dp.start_polling(bot)

