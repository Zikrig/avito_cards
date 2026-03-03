from io import BytesIO

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from .rendering import build_card_from_svg


async def download_photos(bot: Bot, file_ids: list[str]) -> list[bytes]:
    result: list[bytes] = []
    for file_id in file_ids:
        file = await bot.get_file(file_id)
        buffer = BytesIO()
        await bot.download_file(file.file_path, destination=buffer)
        result.append(buffer.getvalue())
    return result


async def generate_and_send_card(
    message: Message,
    state: FSMContext,
    bot: Bot,
    clear_state: bool = True,
) -> None:
    """Собирает карточку по шаблону SVG (3 фото, логотип по умолчанию, все тексты), отправляет PNG и SVG."""
    data = await state.get_data()
    photo_file_ids: list[str] = data.get("photo_file_ids", [])  # [main, minor1, minor2]
    if len(photo_file_ids) != 3:
        await message.answer("Нужно 3 фото: главное и два дополнительных.")
        return
    await message.answer("Собираю карточку, подождите...")
    try:
        photos = await download_photos(bot, photo_file_ids)
        main_b, minor1_b, minor2_b = photos[0], photos[1], photos[2]
        template_id = int(data.get("template_id", 1) or 1)
        skip_logo = bool(data.get("skip_logo"))
        logo_bytes = None
        logo_file_id: str | None = None
        if not skip_logo:
            logo_file_id = data.get("logo_file_id") or data.get("example_logo_file_id")
            if logo_file_id:
                try:
                    logo_list = await download_photos(bot, [logo_file_id])
                    if logo_list:
                        logo_bytes = logo_list[0]
                except Exception:
                    # Если логотип не скачался — просто продолжаем без него.
                    logo_bytes = None
        # Готовим характеристики и подзаголовок на основе CPU / GPU.
        raw_specs: list[str] = list(data.get("spec_list", []))

        def _extract_value(label: str) -> str:
            for item in raw_specs:
                low = item.lower()
                if low.startswith(label.lower()):
                    parts = item.split("—", 1)
                    if len(parts) > 1:
                        return parts[1].strip()
                    # Fallback: всё после двоеточия/пробела.
                    return item[len(label) :].strip()
            return ""

        cpu_val = _extract_value("cpu")
        gpu_val = _extract_value("gpu")
        auto_title_sub = " ".join(part for part in (gpu_val, cpu_val) if part).strip()

        # Форматируем цену: убираем всё, кроме цифр, ставим пробелы по тысячам и знак ₽.
        raw_price = str(data.get("price", "")).strip()
        digits = "".join(ch for ch in raw_price if ch.isdigit())
        if digits:
            try:
                price_int = int(digits)
                formatted_price = f"{price_int:,}".replace(",", " ") + " ₽"
            except ValueError:
                formatted_price = raw_price or ""
        else:
            formatted_price = ""

        svg_path, png_path = await build_card_from_svg(
            main_b,
            minor1_b,
            minor2_b,
            message.from_user.id if message.from_user else 0,
            logo_bytes=logo_bytes,
            title_main=str(data.get("title_main", "")),
            title_sub=auto_title_sub or str(data.get("title_sub", "")),
            text_minor=str(data.get("text_minor", "")),
            text_bottom_line1=str(data.get("text_bottom_line1", "")),
            text_bottom_line2=str(data.get("text_bottom_line2", "")),
            price=formatted_price,
            specs=raw_specs,
            template_id=template_id,
            use_default_logo=not skip_logo,
        )
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка при создании карточки: {exc}")
        return

    photo_file = BufferedInputFile(png_path.read_bytes(), filename=png_path.name)
    svg_file = BufferedInputFile(svg_path.read_text(encoding="utf-8").encode("utf-8"), filename=svg_path.name)
    await message.answer_photo(photo_file, caption="Готово. Карточка по шаблону создана.")
    await message.answer_document(svg_file, caption="SVG-файл карточки (изображения встроены).")
    try:
        svg_path.unlink(missing_ok=True)
        png_path.unlink(missing_ok=True)
    except OSError:
        pass
    if clear_state:
        await state.clear()

