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


def _get_spec_example_for_index(index: int) -> str | None:
    """
    Возвращает пример характеристики для шага с данным индексом (0‑based),
    чтобы можно было показать её в тексте подсказки.
    """
    defaults = _get_defaults_from_example_store()
    specs: list[str] = defaults.get("spec_list", [])
    if 0 <= index < len(specs):
        return specs[index]
    return None


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
        "Отправьте **3 фото ноутбука одним сообщением**: первое будет главным (в большом блоке справа), ещё два — дополнительными.\n"
        "Или нажмите «По умолчанию», чтобы использовать фото из сохранённого примера.",
        reply_markup=cancel_keyboard(default_callback="card_default:photos"),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(CardStates.waiting_for_main_photo, F.photo)
async def main_photo_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    ids: list[str] = list(data.get("photo_file_ids", []))
    ids.append(message.photo[-1].file_id)
    await state.update_data(photo_file_ids=ids)
    if len(ids) < 3:
        # Просто копим фото без лишних сообщений, пока не будет 3 штуки.
        return

    # Есть как минимум 3 фото — берём первые три и переходим к логотипу.
    await state.update_data(photo_file_ids=ids[:3])
    await state.set_state(CardStates.waiting_for_logo)
    await message.answer(
        "Получил 3 фото (1 главное и 2 дополнительных).\n"
        "Теперь отправьте **логотип** (фото или файл PNG/JPG), нажмите «Без логотипа» или «По умолчанию» для логотипа из примера.",
        reply_markup=cancel_keyboard(
            extra_buttons=[[InlineKeyboardButton(text="Без логотипа", callback_data="card_skip_logo")]],
            default_callback="card_default:logo",
        ),
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

    if step == "photos":
        stored = load_examples()
        photo_ids: list[str] = list(stored.get("example_photo_file_ids", []))
        if len(photo_ids) != 3:
            await callback.answer(
                "В примере не сохранены 3 фото. Сначала задайте их в разделе «Примеры».",
                show_alert=True,
            )
            return
        await state.update_data(photo_file_ids=photo_ids[:3])
        await state.set_state(CardStates.waiting_for_logo)
        await callback.answer()
        await callback.message.answer(
            "Фото из примера подставлены.\n"
            "Отправьте **логотип** (фото или файл PNG/JPG), нажмите «Без логотипа» "
            "или «По умолчанию» для логотипа из примера.",
            reply_markup=cancel_keyboard(
                extra_buttons=[[InlineKeyboardButton(text="Без логотипа", callback_data="card_skip_logo")]],
                default_callback="card_default:logo",
            ),
            parse_mode="Markdown",
        )
        return

    if step == "logo":
        stored = load_examples()
        logo_id = stored.get("example_logo_file_id")
        if not logo_id:
            await callback.answer(
                "В примере не сохранён логотип. Сначала задайте его в разделе «Примеры».",
                show_alert=True,
            )
            return
        await state.update_data(logo_file_id=logo_id, skip_logo=False)
        await state.set_state(CardStates.waiting_for_title_main)
        await callback.answer()
        await callback.message.answer(
            f"Укажите модель и бренд ноутбука.\n_Пример: {EXAMPLE_TITLE_MAIN}_",
            reply_markup=cancel_keyboard(default_callback="card_default:title_main"),
            parse_mode="Markdown",
        )
        return

    if step == "spec_example":
        data = await state.get_data()
        stored_defaults = _get_defaults_from_example_store()
        default_specs: list[str] = list(stored_defaults["spec_list"])
        spec_list: list[str] = list(data.get("spec_list", []))
        step = int(data.get("spec_step", 0))
        labels = ["CPU", "GPU", "RAM", "SSD", "Display"]

        if step >= len(labels):
            # Все характеристики уже заполнены — генерируем карточку.
            from_example = data.get("from_example")
            await callback.answer()
            await generate_and_send_card(message=callback.message, state=state, bot=bot, clear_state=not from_example)
            if from_example:
                await callback.message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
                await state.clear()
            return

        label = labels[step]
        example_value = None
        for item in default_specs:
            if item.lower().startswith(label.lower()):
                parts = item.split("—", 1)
                if len(parts) > 1:
                    example_value = parts[1].strip()
                break
        fallback_examples = {
            "CPU": "Ryzen 7 7535HS",
            "GPU": "RTX 4060",
            "RAM": "16 ГБ",
            "SSD": "512 ГБ",
            "Display": '15.6" IPS 144 Гц',
        }
        example_value = example_value or fallback_examples.get(label, "")

        spec_entry = f"{label} — {example_value}"
        spec_list.append(spec_entry)
        await state.update_data(spec_list=spec_list, spec_step=step + 1)
        await _save_example_if_needed(state)
        await callback.answer()

        if step + 1 >= len(labels):
            from_example = data.get("from_example")
            await callback.message.answer(
                f"Примерная характеристика {label} подставлена: _{example_value}_.\n"
                "Все основные характеристики указаны. Генерирую карточку…",
                parse_mode="Markdown",
            )
            await generate_and_send_card(message=callback.message, state=state, bot=bot, clear_state=not from_example)
            if from_example:
                await callback.message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
                await state.clear()
        else:
            next_label = labels[step + 1]
            next_example_value = None
            for item in default_specs:
                if item.lower().startswith(next_label.lower()):
                    parts = item.split("—", 1)
                    if len(parts) > 1:
                        next_example_value = parts[1].strip()
                    break
            next_example_value = next_example_value or fallback_examples.get(next_label, "")

            await callback.message.answer(
                f"Примерная характеристика {label} подставлена: _{example_value}_.\n\n"
                f"Укажите {next_label} (например: _{next_example_value}_).",
                reply_markup=cancel_keyboard(default_callback="card_default:spec_example"),
                parse_mode="Markdown",
            )
        return

    stored_defaults = _get_defaults_from_example_store()
    defaults = {
        "title_main": (
            {"title_main": stored_defaults["title_main"]},
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
                # Характеристики по умолчанию подставляются отдельной кнопкой spec_example.
                "spec_list": [],
            },
            CardStates.waiting_for_spec,
            "Укажите CPU (например: _Ryzen 7 7535HS_).",
            "card_default:spec_example",
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
    await message.answer("Отправьте 3 фото ноутбука (1 главное и 2 дополнительных).")


@router.message(CardStates.waiting_for_minor_photo_1)
@router.message(CardStates.waiting_for_minor_photo_2)
async def _unused_minor_photo_states(message: Message) -> None:
    # Эти состояния больше не используются: все 3 фото собираем на шаге waiting_for_main_photo.
    await message.answer("Сначала выберите формат карточки и отправьте до 3 фото в ответ.")


@router.callback_query(F.data == "card_skip_logo", CardStates.waiting_for_logo)
async def card_skip_logo_callback(callback: CallbackQuery, state: FSMContext) -> None:
    # Пользователь явно выбирает вариант без логотипа:
    # не используем ни логотип из примера, ни логотип по умолчанию.
    await state.update_data(logo_file_id=None, skip_logo=True)
    await state.set_state(CardStates.waiting_for_title_main)
    await callback.message.edit_text(
        f"Введите **название главное** (одной строкой).\n_Пример: {EXAMPLE_TITLE_MAIN}_",
        reply_markup=cancel_keyboard(default_callback="card_default:title_main"),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(CardStates.waiting_for_logo, F.photo)
async def logo_photo_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(logo_file_id=message.photo[-1].file_id, skip_logo=False)
    await state.set_state(CardStates.waiting_for_title_main)
    await message.answer(
        f"Укажите модель и бренд ноутбука.\n_Пример: {EXAMPLE_TITLE_MAIN}_",
        reply_markup=cancel_keyboard(default_callback="card_default:title_main"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_logo, F.document)
async def logo_document_handler(message: Message, state: FSMContext) -> None:
    doc = message.document
    if doc and doc.mime_type and doc.mime_type.startswith("image/"):
        await state.update_data(logo_file_id=doc.file_id, skip_logo=False)
        await state.set_state(CardStates.waiting_for_title_main)
        await message.answer(
            f"Укажите модель и бренд ноутбука.\n_Пример: {EXAMPLE_TITLE_MAIN}_",
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
    await state.set_state(CardStates.waiting_for_text_minor)
    await message.answer(
        f"Введите **текст блока слева** (описание, можно с переносами).\n_Пример: {EXAMPLE_TEXT_MINOR}_",
        reply_markup=cancel_keyboard(default_callback="card_default:text_minor"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_title_main)
async def wrong_title_main(message: Message) -> None:
    await message.answer("Укажите модель и бренд ноутбука текстом.")


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
    # Начинаем пошаговый сбор характеристик: CPU, GPU, RAM, SSD, Display.
    await state.update_data(spec_list=[], spec_step=0)
    await _save_example_if_needed(state)
    await state.set_state(CardStates.waiting_for_spec)
    cpu_example = _get_spec_example_for_index(0) or "Ryzen 7 7535HS"
    await message.answer(
        f"Укажите CPU (например: _{cpu_example}_).",
        reply_markup=cancel_keyboard(default_callback="card_default:spec_example"),
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
    step = int(data.get("spec_step", 0))

    # Позволяем пользователю досрочно завершить ввод характеристик.
    if _spec_done(text) and spec_list:
        from_example = data.get("from_example")
        await generate_and_send_card(message=message, state=state, bot=bot, clear_state=not from_example)
        if from_example:
            await message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
            await state.clear()
        return
    elif _spec_done(text):
        await message.answer("Сначала укажите хотя бы одну характеристику.")
        return

    labels = ["CPU", "GPU", "RAM", "SSD", "Display"]
    if step >= len(labels):
        # На всякий случай, если шаг вышел за пределы — считаем, что всё заполнено.
        from_example = data.get("from_example")
        await generate_and_send_card(message=message, state=state, bot=bot, clear_state=not from_example)
        if from_example:
            await message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
            await state.clear()
        return

    label = labels[step]
    value = text
    spec_entry = f"{label} — {value}"
    spec_list.append(spec_entry)
    await state.update_data(spec_list=spec_list, spec_step=step + 1)
    await _save_example_if_needed(state)

    if step + 1 >= len(labels):
        # Все 5 характеристик собраны — генерируем карточку.
        from_example = data.get("from_example")
        await message.answer("Все основные характеристики указаны. Генерирую карточку…")
        await generate_and_send_card(message=message, state=state, bot=bot, clear_state=not from_example)
        if from_example:
            await message.answer("Раздел «Примеры».", reply_markup=examples_menu_keyboard())
            await state.clear()
        return

    # Иначе спрашиваем следующую характеристику.
    next_label = labels[step + 1]
    example_value = None
    # Пробуем взять пример из сохранённых характеристик.
    defaults = _get_defaults_from_example_store()
    for item in defaults.get("spec_list", []):
        if item.lower().startswith(next_label.lower()):
            parts = item.split("—", 1)
            if len(parts) > 1:
                example_value = parts[1].strip()
            break
    fallback_examples = {
        "CPU": "Ryzen 7 7535HS",
        "GPU": "RTX 4060",
        "RAM": "16 ГБ",
        "SSD": "512 ГБ",
        "Display": '15.6" IPS 144 Гц',
    }
    example_value = example_value or fallback_examples.get(next_label, "")

    await message.answer(
        f"Укажите {next_label} (например: _{example_value}_).",
        reply_markup=cancel_keyboard(default_callback="card_default:spec_example"),
        parse_mode="Markdown",
    )


@router.message(CardStates.waiting_for_spec)
async def wrong_spec(message: Message) -> None:
    await message.answer('Отправьте пару через « — » (например: Экран — 15.6") или «готово».')
