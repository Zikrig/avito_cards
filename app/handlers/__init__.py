from aiogram import Dispatcher

from .card import router as card_router
from .config import router as config_router
from .examples import router as examples_router
from .menu import router as menu_router


def include_routers(dp: Dispatcher) -> None:
    dp.include_router(menu_router)
    dp.include_router(config_router)
    dp.include_router(examples_router)
    dp.include_router(card_router)

