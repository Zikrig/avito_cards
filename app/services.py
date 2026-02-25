from io import BytesIO

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from .context import get_app_config
from .rendering import build_card


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
    features: str,
    description: str,
    price_text: str,
    clear_state: bool = True,
) -> None:
    data = await state.get_data()
    photo_file_ids: list[str] = data.get("photo_file_ids", [])
    await message.answer("Собираю карточку, подождите...")
    try:
        config = get_app_config()
        photo_bytes_list = await download_photos(bot, photo_file_ids)
        output_file, html_file = await build_card(
            config=config,
            photos=photo_bytes_list,
            features=features,
            description=description,
            price=price_text,
            user_id=message.from_user.id if message.from_user else 0,
        )
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка при создании карточки: {exc}")
        return

    photo_file = BufferedInputFile(output_file.read_bytes(), filename=output_file.name)
    html_export_file = BufferedInputFile(html_file.read_bytes(), filename=html_file.name)
    await message.answer_photo(photo_file, caption="Готово. Карточка для Авито создана.")
    await message.answer_document(
        html_export_file,
        caption="HTML-шаблон с путями к изображениям (pic1.jpg, pic2.jpg, pic3.jpg).",
    )
    try:
        output_file.unlink(missing_ok=True)
        html_file.unlink(missing_ok=True)
    except OSError:
        pass
    if clear_state:
        await state.clear()

