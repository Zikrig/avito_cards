from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..services import generate_and_send_card
from ..states import CardStates
from ..ui import cancel_keyboard, examples_menu_keyboard

# Примеры текстов с текущей страницы шаблона (для подсказок в боте)
EXAMPLE_TITLE_MAIN = "Msi Bravo 15.6"
EXAMPLE_TITLE_SUB = "RTX 4060 Ryzen 7 7535HS"
EXAMPLE_TEXT_MINOR = "Это решение подойдёт не только геймерам, но и дизайнерам, стримерам, 3D-моделлерам и видеомонтажёрам."
EXAMPLE_TEXT_BOTTOM_1 = "Гарантия до 12 месяцев"
EXAMPLE_TEXT_BOTTOM_2 = "Доставка или самовывоз"
EXAMPLE_PRICE = "69 990 ₽"

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
async def minor_photo_2_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    ids: list[str] = list(data.get("photo_file_ids", []))
    ids.append(message.photo[-1].file_id)
    await state.update_data(photo_file_ids=ids)
    await state.set_state(CardStates.waiting_for_title_main)
    await message.answer(
        f"Введите **название главное** (одной строкой).\n_Пример: {EXAMPLE_TITLE_MAIN}_",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_minor_photo_2)
async def wrong_minor_photo_2(message: Message) -> None:
    await message.answer("Отправьте фото (второе дополнительное).")


@router.message(CardStates.waiting_for_title_main, F.text)
async def title_main_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(title_main=message.text.strip())
    await state.set_state(CardStates.waiting_for_title_sub)
    await message.answer(
        f"Введите **подзаголовок** (название минорное, одна строка).\n_Пример: {EXAMPLE_TITLE_SUB}_",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_title_main)
async def wrong_title_main(message: Message) -> None:
    await message.answer("Отправьте текст названия.")


@router.message(CardStates.waiting_for_title_sub, F.text)
async def title_sub_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(title_sub=message.text.strip())
    await state.set_state(CardStates.waiting_for_text_minor)
    await message.answer(
        f"Введите **текст блока слева** (описание, можно с переносами).\n_Пример: {EXAMPLE_TEXT_MINOR}_",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_title_sub)
async def wrong_title_sub(message: Message) -> None:
    await message.answer("Отправьте текст подзаголовка.")


@router.message(CardStates.waiting_for_text_minor, F.text)
async def text_minor_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(text_minor=message.text.strip())
    await state.set_state(CardStates.waiting_for_text_bottom_line1)
    await message.answer(
        f"Введите **первую строку блока справа внизу**.\n_Пример: {EXAMPLE_TEXT_BOTTOM_1}_",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_text_minor)
async def wrong_text_minor(message: Message) -> None:
    await message.answer("Отправьте текст.")


@router.message(CardStates.waiting_for_text_bottom_line1, F.text)
async def text_bottom_1_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(text_bottom_line1=message.text.strip())
    await state.set_state(CardStates.waiting_for_text_bottom_line2)
    await message.answer(
        f"Введите **вторую строку блока справа внизу**.\n_Пример: {EXAMPLE_TEXT_BOTTOM_2}_",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_text_bottom_line1)
async def wrong_text_bottom_1(message: Message) -> None:
    await message.answer("Отправьте текст.")


@router.message(CardStates.waiting_for_text_bottom_line2, F.text)
async def text_bottom_2_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(text_bottom_line2=message.text.strip())
    await state.set_state(CardStates.waiting_for_price)
    await message.answer(
        f"Введите **цену** (как на карточке).\n_Пример: {EXAMPLE_PRICE}_",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_text_bottom_line2)
async def wrong_text_bottom_2(message: Message) -> None:
    await message.answer("Отправьте текст.")


@router.message(CardStates.waiting_for_price, F.text)
async def price_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(price=message.text.strip())
    await state.update_data(spec_list=[])
    await state.set_state(CardStates.waiting_for_spec)
    await message.answer(
        "Введите **техническую характеристику 1** (или «готово», чтобы закончить; всего до 5).",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_price)
async def wrong_price(message: Message) -> None:
    await message.answer("Отправьте цену текстом.")


def _spec_done(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in ("готово", "готоо", "-", "")


@router.message(CardStates.waiting_for_spec, F.text)
async def spec_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    text = message.text.strip()
    data = await state.get_data()
    spec_list: list[str] = list(data.get("spec_list", []))

    if _spec_done(text):
        if not spec_list:
            await message.answer("Добавьте хотя бы одну характеристику или введите текст характеристики.")
            return
        from_example = data.get("from_example")
        await generate_and_send_card(message=message, state=state, bot=bot, clear_state=not from_example)
        if from_example:
            await message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
            await state.clear()
        return

    spec_list.append(text)
    await state.update_data(spec_list=spec_list)

    if len(spec_list) >= 5:
        from_example = data.get("from_example")
        await generate_and_send_card(message=message, state=state, bot=bot, clear_state=not from_example)
        if from_example:
            await message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
            await state.clear()
        return

    n = len(spec_list) + 1
    await message.answer(
        f"Характеристика {len(spec_list)} добавлена. Введите **характеристику {n}** (или «готово»).",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_spec)
async def wrong_spec(message: Message) -> None:
    await message.answer("Отправьте текст характеристики или «готово».")
