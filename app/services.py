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
    """Собирает карточку по шаблону SVG (главное фото + 2 доп.), отправляет PNG и SVG."""
    data = await state.get_data()
    photo_file_ids: list[str] = data.get("photo_file_ids", [])  # [main, minor1, minor2]
    if len(photo_file_ids) != 3:
        await message.answer("Нужно 3 фото: главное и два дополнительных.")
        return
    await message.answer("Собираю карточку, подождите...")
    try:
        photos = await download_photos(bot, photo_file_ids)
        main_b, minor1_b, minor2_b = photos[0], photos[1], photos[2]
        svg_path, png_path = await build_card_from_svg(
            main_photo=main_b,
            minor_photo_1=minor1_b,
            minor_photo_2=minor2_b,
            user_id=message.from_user.id if message.from_user else 0,
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

