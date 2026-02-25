from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..ui import config_menu_keyboard, examples_menu_keyboard, main_menu_keyboard


router = Router()


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню. Выберите действие:", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Главное меню. Выберите действие:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_config")
async def menu_config(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Что хотите изменить?", reply_markup=config_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_examples")
async def menu_examples(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(None)
    await callback.message.edit_text(
        "Раздел «Примеры». Выберите пример или задайте данные:",
        reply_markup=examples_menu_keyboard(),
    )
    await callback.answer()

