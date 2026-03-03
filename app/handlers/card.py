from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from ..example_store import load_examples, save_examples
from ..services import generate_and_send_card
from ..states import CardStates
from ..ui import cancel_keyboard, examples_menu_keyboard, template_select_keyboard

# Примеры текстов с текущей страницы шаблона (для подсказок в боте)
EXAMPLE_TITLE_MAIN = "Msi Bravo 15.6"
EXAMPLE_TITLE_SUB = "RTX 4060 Ryzen 7 7535HS"
EXAMPLE_TEXT_MINOR = "Это решение подойдёт не только геймерам, но и дизайнерам, стримерам, 3D-моделлерам и видеомонтажёрам."
EXAMPLE_TEXT_BOTTOM_1 = "Гарантия до 12 месяцев"
EXAMPLE_TEXT_BOTTOM_2 = "Доставка или самовывоз"
EXAMPLE_PRICE = "69 990 ₽"

router = Router()


def _get_defaults_from_example_store() -> dict[str, Any]:
    """
    Берёт значения по умолчанию из сохранённого примера (examples.json),
    а если их нет — использует константы из этого файла.
    """
    stored = load_examples()
    return {
        "title_main": str(stored.get("title_main") or EXAMPLE_TITLE_MAIN),
        "title_sub": str(stored.get("title_sub") or EXAMPLE_TITLE_SUB),
        "text_minor": str(stored.get("text_minor") or EXAMPLE_TEXT_MINOR),
        "text_bottom_line1": str(stored.get("text_bottom_line1") or EXAMPLE_TEXT_BOTTOM_1),
        "text_bottom_line2": str(stored.get("text_bottom_line2") or EXAMPLE_TEXT_BOTTOM_2),
        "price": str(stored.get("price") or EXAMPLE_PRICE),
        # Характеристики: берём список, если он был сохранён вместе с примером.
        "spec_list": list(stored.get("spec_list") or []),
    }


async def _save_example_if_needed(state: FSMContext) -> None:
    """Если данные заполняются из меню примера, сохраняем их на диск."""
    data = await state.get_data()
    if data.get("from_example"):
        save_examples(data)


@router.callback_query(F.data == "menu_create_card")
async def menu_create_card(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CardStates.waiting_for_template)
    await callback.message.edit_text(
        "Выберите вариант макета карточки:",
        reply_markup=template_select_keyboard(prefix="card_tpl"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("card_tpl:"))
async def card_template_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор варианта SVG-шаблона перед созданием карточки."""
    raw = (callback.data or "").removeprefix("card_tpl:")
    if raw not in {"1", "2", "3"}:
        await callback.answer()
        return
    await state.update_data(template_id=int(raw), photo_file_ids=[])
    await state.set_state(CardStates.waiting_for_main_photo)
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


@router.callback_query(F.data.startswith("card_default:"))
async def card_default_callback(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Обработка кнопки «По умолчанию»: подставить пример и перейти к следующему шагу."""
    step = (callback.data or "").removeprefix("card_default:")
    if not step:
        await callback.answer()
        return

    if step == "spec_done":
        data = await state.get_data()
        spec_list: list[str] = list(data.get("spec_list", []))
        if not spec_list:
            await callback.answer("Добавьте хотя бы одну характеристику.", show_alert=True)
            return
        from_example = data.get("from_example")
        await callback.answer()
        # При генерации из примера не чистим данные примера, чтобы не приходилось заново задавать фото и тексты.
        await generate_and_send_card(message=callback.message, state=state, bot=bot, clear_state=not from_example)
        if from_example:
            preserved_keys = (
                "example_photo_file_ids",
                "example_logo_file_id",
                "example_features",
                "example_description",
                "example_price_text",
            )
            preserved = {k: v for k, v in data.items() if k in preserved_keys}
            await state.clear()
            if preserved:
                await state.update_data(**preserved)
            await callback.message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
        return

    stored_defaults = _get_defaults_from_example_store()
    defaults = {
        "title_main": (
            {"title_main": stored_defaults["title_main"]},
            CardStates.waiting_for_title_sub,
            f"Введите **подзаголовок** (название минорное, одна строка).\n_Пример: {EXAMPLE_TITLE_SUB}_",
            "card_default:title_sub",
        ),
        "title_sub": (
            {"title_sub": stored_defaults["title_sub"]},
            CardStates.waiting_for_text_minor,
            f"Введите **текст блока слева** (описание, можно с переносами).\n_Пример: {EXAMPLE_TEXT_MINOR}_",
            "card_default:text_minor",
        ),
        "text_minor": (
            {
                "text_minor": stored_defaults["text_minor"],
                "text_bottom_line1": stored_defaults["text_bottom_line1"],
                "text_bottom_line2": stored_defaults["text_bottom_line2"],
            },
            CardStates.waiting_for_price,
            f"Введите **цену** (как на карточке).\n_Пример: {EXAMPLE_PRICE}_",
            "card_default:price",
        ),
        "price": (
            {
                "price": stored_defaults["price"],
                # Если в сохранённом примере уже есть характеристики — подставляем их сразу.
                "spec_list": list(stored_defaults["spec_list"]),
            },
            CardStates.waiting_for_spec,
            "Введите **характеристику 1** — две части через « — » (например: _Экран — 15.6 дюймов_). Или «готово», чтобы закончить (всего до 5 пар).",
            "card_default:spec_done",
        ),
    }
    if step not in defaults:
        await callback.answer()
        return
    updates, next_state, next_text, next_callback = defaults[step]
    await state.update_data(**updates)
    await _save_example_if_needed(state)
    await state.set_state(next_state)
    await callback.answer()
    await callback.message.answer(
        next_text,
        reply_markup=cancel_keyboard(default_callback=next_callback),
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
    await state.set_state(CardStates.waiting_for_logo)
    await message.answer(
        "Отправьте **логотип** (фото или файл PNG/JPG) или нажмите «Без логотипа», чтобы использовать стандартный.",
        reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="Без логотипа", callback_data="card_skip_logo")]]),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_minor_photo_2)
async def wrong_minor_photo_2(message: Message) -> None:
    await message.answer("Отправьте фото (второе дополнительное).")


@router.callback_query(F.data == "card_skip_logo", CardStates.waiting_for_logo)
async def card_skip_logo_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(logo_file_id=None)
    await state.set_state(CardStates.waiting_for_title_main)
    await callback.message.edit_text(
        f"Введите **название главное** (одной строкой).\n_Пример: {EXAMPLE_TITLE_MAIN}_",
        reply_markup=cancel_keyboard(default_callback="card_default:title_main"),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(CardStates.waiting_for_logo, F.photo)
async def logo_photo_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(logo_file_id=message.photo[-1].file_id)
    await state.set_state(CardStates.waiting_for_title_main)
    await message.answer(
        f"Введите **название главное** (одной строкой).\n_Пример: {EXAMPLE_TITLE_MAIN}_",
        reply_markup=cancel_keyboard(default_callback="card_default:title_main"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_logo, F.document)
async def logo_document_handler(message: Message, state: FSMContext) -> None:
    doc = message.document
    if doc and doc.mime_type and doc.mime_type.startswith("image/"):
        await state.update_data(logo_file_id=doc.file_id)
        await state.set_state(CardStates.waiting_for_title_main)
        await message.answer(
            f"Введите **название главное** (одной строкой).\n_Пример: {EXAMPLE_TITLE_MAIN}_",
            reply_markup=cancel_keyboard(default_callback="card_default:title_main"),
            parse_mode="Markdown",
        )
    else:
        await message.answer("Отправьте изображение (PNG, JPG и т.п.) или нажмите «Без логотипа».")


@router.message(CardStates.waiting_for_logo)
async def wrong_logo(message: Message) -> None:
    await message.answer("Отправьте логотип фото/документом (изображение) или нажмите «Без логотипа».")


@router.message(CardStates.waiting_for_title_main, F.text)
async def title_main_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(title_main=message.text.strip())
    await _save_example_if_needed(state)
    await state.set_state(CardStates.waiting_for_title_sub)
    await message.answer(
        f"Введите **подзаголовок** (название минорное, одна строка).\n_Пример: {EXAMPLE_TITLE_SUB}_",
        reply_markup=cancel_keyboard(default_callback="card_default:title_sub"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_title_main)
async def wrong_title_main(message: Message) -> None:
    await message.answer("Отправьте текст названия.")


@router.message(CardStates.waiting_for_title_sub, F.text)
async def title_sub_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(title_sub=message.text.strip())
    await _save_example_if_needed(state)
    await state.set_state(CardStates.waiting_for_text_minor)
    await message.answer(
        f"Введите **текст блока слева** (описание, можно с переносами).\n_Пример: {EXAMPLE_TEXT_MINOR}_",
        reply_markup=cancel_keyboard(default_callback="card_default:text_minor"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_title_sub)
async def wrong_title_sub(message: Message) -> None:
    await message.answer("Отправьте текст подзаголовка.")


@router.message(CardStates.waiting_for_text_minor, F.text)
async def text_minor_handler(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    await state.update_data(
        text_minor=text,
        text_bottom_line1=EXAMPLE_TEXT_BOTTOM_1,
        text_bottom_line2=EXAMPLE_TEXT_BOTTOM_2,
    )
    await _save_example_if_needed(state)
    if len(text) >= 50:
        await message.answer(
            "⚠ Описание длинное (50+ символов). На карточке отображаются только первые 3 строки."
        )
    await state.set_state(CardStates.waiting_for_price)
    await message.answer(
        f"Введите **цену** (как на карточке).\n_Пример: {EXAMPLE_PRICE}_",
        reply_markup=cancel_keyboard(default_callback="card_default:price"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_text_minor)
async def wrong_text_minor(message: Message) -> None:
    await message.answer("Отправьте текст.")


@router.message(CardStates.waiting_for_text_bottom_line1, F.text)
async def text_bottom_1_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(text_bottom_line1=message.text.strip())
    await _save_example_if_needed(state)
    await state.set_state(CardStates.waiting_for_text_bottom_line2)
    await message.answer(
        f"Введите **вторую строку блока справа внизу**.\n_Пример: {EXAMPLE_TEXT_BOTTOM_2}_",
        reply_markup=cancel_keyboard(default_callback="card_default:text_bottom_line2"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_text_bottom_line1)
async def wrong_text_bottom_1(message: Message) -> None:
    await message.answer("Отправьте текст.")


@router.message(CardStates.waiting_for_text_bottom_line2, F.text)
async def text_bottom_2_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(text_bottom_line2=message.text.strip())
    await _save_example_if_needed(state)
    await state.set_state(CardStates.waiting_for_price)
    await message.answer(
        f"Введите **цену** (как на карточке).\n_Пример: {EXAMPLE_PRICE}_",
        reply_markup=cancel_keyboard(default_callback="card_default:price"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_text_bottom_line2)
async def wrong_text_bottom_2(message: Message) -> None:
    await message.answer("Отправьте текст.")


@router.message(CardStates.waiting_for_price, F.text)
async def price_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(price=message.text.strip())
    await state.update_data(spec_list=[])
    await _save_example_if_needed(state)
    await state.set_state(CardStates.waiting_for_spec)
    await message.answer(
        "Введите **характеристику 1** — две части через « — » (например: _Экран — 15.6 дюймов_). Или «готово», чтобы закончить (всего до 5 пар).",
        reply_markup=cancel_keyboard(default_callback="card_default:spec_done"),
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
    await _save_example_if_needed(state)

    if len(spec_list) >= 5:
        from_example = data.get("from_example")
        await generate_and_send_card(message=message, state=state, bot=bot, clear_state=not from_example)
        if from_example:
            await message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
            await state.clear()
        return

    n = len(spec_list) + 1
    await message.answer(
        f"Пара добавлена. Введите **характеристику {n}** — две части через « — » (или «готово»).",
        reply_markup=cancel_keyboard(default_callback="card_default:spec_done"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_spec)
async def wrong_spec(message: Message) -> None:
    await message.answer('Отправьте пару через « — » (например: Экран — 15.6") или «готово».')
