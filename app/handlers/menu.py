from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..auth_store import add_admin_request, get_role, ensure_user_role
from ..ui import examples_menu_keyboard, main_menu_keyboard


router = Router()


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0
    role = get_role(user_id)
    if role == "guest":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="ВОЙТИ", callback_data="login_start")],
            ]
        )
        await message.answer("Это служебный бот.", reply_markup=kb)
        return

    await message.answer("Главное меню. Выберите действие:", reply_markup=main_menu_keyboard(role))


@router.callback_query(F.data == "login_start")
async def login_start(callback: CallbackQuery, state: FSMContext) -> None:
    _ = state
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Пользователь", callback_data="login_user"),
                InlineKeyboardButton(text="Администратор", callback_data="login_admin"),
            ],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel")],
        ]
    )
    await callback.message.edit_text("Выберите роль для входа:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "login_user")
async def login_user(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    ensure_user_role(user_id, as_admin=False)
    await callback.answer()
    role = get_role(user_id)
    await callback.message.edit_text("Вы зарегистрированы как пользователь.", reply_markup=main_menu_keyboard(role))


@router.callback_query(F.data == "login_admin")
async def login_admin(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    username = callback.from_user.username or ""
    display = f"@{username}" if username else str(user_id)
    add_admin_request(user_id, display)
    await callback.answer()
    await callback.message.edit_text(
        "Заявка на роль администратора отправлена. Подождите, пока один из администраторов её одобрит."
    )


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    role = get_role(user_id)
    if role == "guest":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="ВОЙТИ", callback_data="login_start")]]
        )
        await callback.message.edit_text("Это служебный бот.", reply_markup=kb)
    else:
        await callback.message.edit_text(
            "Главное меню. Выберите действие:", reply_markup=main_menu_keyboard(role)
        )
    await callback.answer()


@router.callback_query(F.data == "menu_examples")
async def menu_examples(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(None)
    await callback.message.edit_text(
        "Раздел «Примеры». Выберите пример или задайте данные:",
        reply_markup=examples_menu_keyboard(),
    )
    await callback.answer()

