from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from ..services import generate_and_send_card
from ..states import CardStates, ExampleStates
from ..ui import cancel_keyboard, example_builder_keyboard, examples_menu_keyboard


router = Router()


@router.callback_query(F.data == "example_edit_data")
async def example_edit_data(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(None)
    await callback.message.edit_text("Меню примера: выберите, что изменить.", reply_markup=example_builder_keyboard(await state.get_data()))
    await callback.answer()


@router.callback_query(F.data == "example_edit_photos")
async def example_edit_photos(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ExampleStates.waiting_for_photos)
    await state.update_data(example_photo_file_ids=[])
    await callback.message.edit_text(
        "Отправьте **3 фото по порядку**: 1) главное, 2) первое доп., 3) второе доп. Затем нажмите «Готово с фото».",
        reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="✅ Готово с фото", callback_data="example_photos_done")]]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "example_edit_features")
async def example_edit_features(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ExampleStates.waiting_for_features)
    await callback.message.edit_text("Введите характеристики товара текстом.", reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="⬅️ К данным", callback_data="example_back_builder")]]))
    await callback.answer()


@router.callback_query(F.data == "example_edit_description")
async def example_edit_description(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ExampleStates.waiting_for_description)
    await callback.message.edit_text("Введите описание товара текстом.", reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="⬅️ К данным", callback_data="example_back_builder")]]))
    await callback.answer()


@router.callback_query(F.data == "example_edit_price")
async def example_edit_price(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ExampleStates.waiting_for_price)
    await callback.message.edit_text("Введите название и цену одной строкой.", reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="⬅️ К данным", callback_data="example_back_builder")]]))
    await callback.answer()


@router.callback_query(F.data == "example_edit_texts")
async def example_edit_texts(callback: CallbackQuery, state: FSMContext) -> None:
    """Запуск заполнения текстов примера (те же шаги, что и при создании карточки)."""
    data = await state.get_data()
    photo_ids: list[str] = data.get("example_photo_file_ids", [])
    if len(photo_ids) != 3:
        await callback.answer("Сначала задайте 3 фото: главное и два дополнительных.", show_alert=True)
        return
    await state.update_data(photo_file_ids=photo_ids[:3], from_example=True)
    await state.set_state(CardStates.waiting_for_title_main)
    await callback.message.edit_text(
        "Введите **название главное** (одной строкой).\n_Пример: Msi Bravo 15.6_",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "example_back_builder")
@router.callback_query(F.data == "example_photos_done")
async def example_back_builder(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data == "example_photos_done":
        count = len((await state.get_data()).get("example_photo_file_ids", []))
        if count != 3:
            await callback.answer(f"Нужно ровно 3 фото. Сейчас: {count}.", show_alert=True)
            return
    await state.set_state(None)
    await callback.message.edit_text("Меню примера: выберите, что изменить.", reply_markup=example_builder_keyboard(await state.get_data()))
    await callback.answer()


@router.callback_query(F.data == "example_gen")
async def example_generate(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    photos: list[str] = data.get("example_photo_file_ids", [])
    if len(photos) != 3:
        await callback.answer("Задайте ровно 3 фото: главное и два дополнительных.", show_alert=True)
        return
    # Должны быть заполнены тексты (через «Заполнить тексты»)
    if not data.get("title_main"):
        await callback.answer("Сначала нажмите «Заполнить тексты» и введите все данные.", show_alert=True)
        return

    await state.update_data(photo_file_ids=photos[:3])
    await callback.answer()
    await generate_and_send_card(
        message=callback.message,
        state=state,
        bot=bot,
        clear_state=False,
    )
    await callback.message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())


@router.message(ExampleStates.waiting_for_photos, F.photo)
async def example_collect_photos(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_ids: list[str] = data.get("example_photo_file_ids", [])
    if len(photo_ids) >= 3:
        await message.answer("Лимит: 3 фото.")
        return
    photo_ids.append(message.photo[-1].file_id)
    await state.update_data(example_photo_file_ids=photo_ids)
    await message.answer(
        f"Фото добавлено: {len(photo_ids)}/3",
        reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="✅ Готово с фото", callback_data="example_photos_done")]]),
    )


@router.message(ExampleStates.waiting_for_features, F.text)
async def example_features_input(message: Message, state: FSMContext) -> None:
    value = message.text.strip()
    if not value:
        await message.answer("Характеристики пустые.")
        return
    await state.update_data(example_features=value)
    await state.set_state(None)
    await message.answer("Характеристики сохранены.", reply_markup=example_builder_keyboard(await state.get_data()))


@router.message(ExampleStates.waiting_for_description, F.text)
async def example_description_input(message: Message, state: FSMContext) -> None:
    value = message.text.strip()
    if not value:
        await message.answer("Описание пустое.")
        return
    await state.update_data(example_description=value)
    await state.set_state(None)
    await message.answer("Описание сохранено.", reply_markup=example_builder_keyboard(await state.get_data()))


@router.message(ExampleStates.waiting_for_price, F.text)
async def example_price_input(message: Message, state: FSMContext) -> None:
    value = message.text.strip()
    if not value:
        await message.answer("Название+цена пустые.")
        return
    await state.update_data(example_price_text=value)
    await state.set_state(None)
    await message.answer("Название+цена сохранены.", reply_markup=example_builder_keyboard(await state.get_data()))


@router.message(ExampleStates.waiting_for_photos)
@router.message(ExampleStates.waiting_for_features)
@router.message(ExampleStates.waiting_for_description)
@router.message(ExampleStates.waiting_for_price)
async def example_wrong_input(message: Message) -> None:
    await message.answer("Неверный тип данных для текущего шага.")

