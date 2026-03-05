from aiogram import Dispatcher

from .admin import router as admin_router
from .card import router as card_router
from .config import router as config_router
from .examples import router as examples_router
from .menu import fallback_router, router as menu_router


def include_routers(dp: Dispatcher) -> None:
    # Сначала основные сценарии:
    dp.include_router(menu_router)
    dp.include_router(config_router)
    dp.include_router(examples_router)
    dp.include_router(card_router)
    dp.include_router(admin_router)
    # В самом конце — fallback на любое сообщение без состояния.
    dp.include_router(fallback_router)

