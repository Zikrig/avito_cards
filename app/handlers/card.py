from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..services import generate_and_send_card
from ..states import CardStates
from ..ui import cancel_keyboard


router = Router()


@router.callback_query(F.data == "menu_create_card")
async def menu_create_card(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CardStates.waiting_for_main_photo)
    await state.update_data(photo_file_ids=[])
    await callback.message.edit_text(
        "Отправьте **главное фото** товара (оно будет в большом блоке справа).",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(CardStates.waiting_for_main_photo, F.photo)
async def main_photo_handler(message: Message, state: FSMContext) -> None:
    file_id = message.photo[-1].file_id
    await state.update_data(photo_file_ids=[file_id])
    await state.set_state(CardStates.waiting_for_minor_photo_1)
    await message.answer(
        "Главное фото принято. Отправьте **первое дополнительное фото** (малый блок слева внизу).",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_main_photo)
async def wrong_main_photo(message: Message) -> None:
    await message.answer("Отправьте одно фото (главное изображение товара).")


@router.message(CardStates.waiting_for_minor_photo_1, F.photo)
async def minor_photo_1_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    ids: list[str] = list(data.get("photo_file_ids", []))
    ids.append(message.photo[-1].file_id)
    await state.update_data(photo_file_ids=ids)
    await state.set_state(CardStates.waiting_for_minor_photo_2)
    await message.answer(
        "Первое доп. фото принято. Отправьте **второе дополнительное фото** (второй малый блок слева внизу).",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_minor_photo_1)
async def wrong_minor_photo_1(message: Message) -> None:
    await message.answer("Отправьте фото (первое дополнительное).")


@router.message(CardStates.waiting_for_minor_photo_2, F.photo)
async def minor_photo_2_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    ids: list[str] = list(data.get("photo_file_ids", []))
    ids.append(message.photo[-1].file_id)
    await state.update_data(photo_file_ids=ids)
    await generate_and_send_card(message=message, state=state, bot=bot, clear_state=True)


@router.message(CardStates.waiting_for_minor_photo_2)
async def wrong_minor_photo_2(message: Message) -> None:
    await message.answer("Отправьте фото (второе дополнительное).")
