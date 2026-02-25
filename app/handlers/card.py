from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from ..services import generate_and_send_card
from ..states import CardStates
from ..ui import cancel_keyboard


router = Router()


@router.callback_query(F.data == "menu_create_card")
async def menu_create_card(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CardStates.waiting_for_photos)
    await state.update_data(photo_file_ids=[])
    await callback.message.edit_text(
        "Отправьте 1–3 фотографии товара по одной.",
        reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="✅ Готово", callback_data="photos_done")]]),
    )
    await callback.answer()


@router.callback_query(CardStates.waiting_for_photos, F.data == "photos_done")
async def photos_done_callback(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    photo_file_ids = data.get("photo_file_ids", [])
    if len(photo_file_ids) < 1:
        await callback.answer("Нужно хотя бы одно фото.", show_alert=True)
        return
    await state.set_state(CardStates.waiting_for_features)
    await callback.message.edit_text("Отправьте текстовые ХАРАКТЕРИСТИКИ товара (списком или абзацем).", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(CardStates.waiting_for_photos, F.photo)
async def collect_photo_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_file_ids: list[str] = data.get("photo_file_ids", [])
    if len(photo_file_ids) >= 3:
        await message.answer(
            "Достигнут лимит: 3 фото.",
            reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="✅ Готово", callback_data="photos_done")]]),
        )
        return
    photo_file_ids.append(message.photo[-1].file_id)
    await state.update_data(photo_file_ids=photo_file_ids)
    await message.answer(
        f"Фото добавлено: {len(photo_file_ids)}/3",
        reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="✅ Готово", callback_data="photos_done")]]),
    )


@router.message(CardStates.waiting_for_photos)
async def wrong_photos_input_handler(message: Message) -> None:
    await message.answer("Отправьте фото или нажмите кнопку «Готово».")


@router.message(CardStates.waiting_for_features, F.text)
async def features_handler(message: Message, state: FSMContext) -> None:
    value = message.text.strip()
    if not value:
        await message.answer("Характеристики пустые. Отправьте текст.")
        return
    await state.update_data(features=value)
    await state.set_state(CardStates.waiting_for_description)
    await message.answer("Теперь отправьте ОПИСАНИЕ товара.", reply_markup=cancel_keyboard())


@router.message(CardStates.waiting_for_description, F.text)
async def description_handler(message: Message, state: FSMContext) -> None:
    value = message.text.strip()
    if not value:
        await message.answer("Описание пустое. Отправьте текст.")
        return
    await state.update_data(description=value)
    await state.set_state(CardStates.waiting_for_price)
    await message.answer("Отправьте название и цену.", reply_markup=cancel_keyboard())


@router.message(CardStates.waiting_for_description)
async def wrong_description_input_handler(message: Message) -> None:
    await message.answer("Отправьте описание обычным текстом.")


@router.message(CardStates.waiting_for_price, F.text)
async def price_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    price_text = message.text.strip()
    if not price_text:
        await message.answer("Цена пустая. Отправьте текст.")
        return
    data = await state.get_data()
    await generate_and_send_card(
        message=message,
        state=state,
        bot=bot,
        features=str(data.get("features", "")),
        description=str(data.get("description", "")),
        price_text=price_text,
        clear_state=True,
    )


@router.message(CardStates.waiting_for_price)
async def wrong_price_input_handler(message: Message) -> None:
    await message.answer("Отправьте цену текстом.")

