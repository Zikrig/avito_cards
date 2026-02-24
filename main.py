import asyncio
import base64
import html
import json
import os
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from playwright.async_api import async_playwright


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
APP_CONFIG: "AppConfig | None" = None


@dataclass
class AppConfig:
    bot_token: str
    raw: dict[str, Any]

    @staticmethod
    def load(path: Path, env_path: Path | None = None) -> "AppConfig":
        if env_path and env_path.exists():
            load_dotenv(env_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise ValueError(
                "Set BOT_TOKEN in .env (see .env.example). "
            )
        return AppConfig(bot_token=token, raw=data)


class CardStates(StatesGroup):
    waiting_for_photos = State()
    waiting_for_features = State()
    waiting_for_description = State()
    waiting_for_price = State()


class ConfigStates(StatesGroup):
    waiting_for_value = State()


router = Router()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧩 Создать карточку", callback_data="menu_create_card")],
            [InlineKeyboardButton(text="⚙️ Настройки конфигурации", callback_data="menu_config")],
        ]
    )


def cancel_keyboard(extra_buttons: list[list[InlineKeyboardButton]] | None = None) -> InlineKeyboardMarkup:
    rows = extra_buttons[:] if extra_buttons else []
    rows.append([InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню. Выберите действие:", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu_create_card")
async def menu_create_card(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CardStates.waiting_for_photos)
    await state.update_data(photo_file_ids=[])
    await callback.message.edit_text(
        "Отправьте 1–3 фотографии товара по одной.",
        reply_markup=cancel_keyboard(
            extra_buttons=[
                [InlineKeyboardButton(text="✅ Готово", callback_data="photos_done")]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Главное меню. Выберите действие:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_config")
async def menu_config(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📐 Размеры и фон", callback_data="cfg_section_output")],
            [InlineKeyboardButton(text="💰 Цена", callback_data="cfg_section_price")],
            [InlineKeyboardButton(text="📝 Описание", callback_data="cfg_section_desc")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel")],
        ]
    )
    await callback.message.edit_text("Что хотите изменить?", reply_markup=kb)
    await callback.answer()


def _config_section_keyboard(section: str, raw: dict[str, Any]) -> InlineKeyboardMarkup:
    if section == "output":
        cfg = raw["output"]
        rows = [
            [InlineKeyboardButton(text=f"width: {cfg['width']}", callback_data="cfg_edit:output:width")],
            [InlineKeyboardButton(text=f"height: {cfg['height']}", callback_data="cfg_edit:output:height")],
            [
                InlineKeyboardButton(
                    text=f"background_color: {cfg['background_color']}",
                    callback_data="cfg_edit:output:background_color",
                )
            ],
            [InlineKeyboardButton(text=f"padding: {cfg['padding']}", callback_data="cfg_edit:output:padding")],
            [InlineKeyboardButton(text=f"gap: {cfg['gap']}", callback_data="cfg_edit:output:gap")],
            [InlineKeyboardButton(text=f"photo_gap: {cfg['photo_gap']}", callback_data="cfg_edit:output:photo_gap")],
            [
                InlineKeyboardButton(
                    text=f"left_column_ratio: {cfg['left_column_ratio']}",
                    callback_data="cfg_edit:output:left_column_ratio",
                )
            ],
        ]
    elif section == "price":
        cfg = raw["cards"]["price_block"]
        rows = [
            [
                InlineKeyboardButton(
                    text=f"background_color: {cfg['background_color']}",
                    callback_data="cfg_edit:price:background_color",
                )
            ],
            [InlineKeyboardButton(text=f"text_color: {cfg['text_color']}", callback_data="cfg_edit:price:text_color")],
            [InlineKeyboardButton(text=f"font_size: {cfg['font_size']}", callback_data="cfg_edit:price:font_size")],
            [InlineKeyboardButton(text=f"padding: {cfg['padding']}", callback_data="cfg_edit:price:padding")],
            [InlineKeyboardButton(text=f"border: {cfg['border']}", callback_data="cfg_edit:price:border")],
            [
                InlineKeyboardButton(
                    text=f"border_radius: {cfg['border_radius']}",
                    callback_data="cfg_edit:price:border_radius",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"text_stroke_width: {cfg['text_stroke_width']}",
                    callback_data="cfg_edit:price:text_stroke_width",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"text_stroke_color: {cfg['text_stroke_color']}",
                    callback_data="cfg_edit:price:text_stroke_color",
                )
            ],
        ]
    else:
        cfg = raw["cards"]["description_block"]
        rows = [
            [
                InlineKeyboardButton(
                    text=f"background_color: {cfg['background_color']}",
                    callback_data="cfg_edit:desc:background_color",
                )
            ],
            [InlineKeyboardButton(text=f"text_color: {cfg['text_color']}", callback_data="cfg_edit:desc:text_color")],
            [InlineKeyboardButton(text=f"font_size: {cfg['font_size']}", callback_data="cfg_edit:desc:font_size")],
            [
                InlineKeyboardButton(
                    text=f"line_height: {cfg['line_height']}",
                    callback_data="cfg_edit:desc:line_height",
                )
            ],
            [InlineKeyboardButton(text=f"padding: {cfg['padding']}", callback_data="cfg_edit:desc:padding")],
            [InlineKeyboardButton(text=f"border: {cfg['border']}", callback_data="cfg_edit:desc:border")],
            [
                InlineKeyboardButton(
                    text=f"border_radius: {cfg['border_radius']}",
                    callback_data="cfg_edit:desc:border_radius",
                )
            ],
        ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_config")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _config_section_data(section: str, raw: dict[str, Any]) -> dict[str, Any]:
    if section == "output":
        return raw["output"]
    if section == "price":
        return raw["cards"]["price_block"]
    return raw["cards"]["description_block"]


def _convert_config_value(raw_value: str, old_value: Any) -> Any:
    value = raw_value.strip()
    if isinstance(old_value, bool):
        low = value.lower()
        if low in {"true", "1", "yes", "y"}:
            return True
        if low in {"false", "0", "no", "n"}:
            return False
        raise ValueError("Ожидалось true/false")
    if isinstance(old_value, int):
        return int(value)
    if isinstance(old_value, float):
        return float(value.replace(",", "."))
    return value


def _save_config_to_file(raw: dict[str, Any]) -> None:
    (BASE_DIR / "config.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@router.callback_query(F.data == "cfg_section_output")
async def cfg_section_output(callback: CallbackQuery, state: FSMContext) -> None:
    if APP_CONFIG is None:
        await callback.answer("Конфиг не загружен", show_alert=True)
        return
    kb = _config_section_keyboard("output", APP_CONFIG.raw)
    await callback.message.edit_text("Параметры output:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "cfg_section_price")
async def cfg_section_price(callback: CallbackQuery, state: FSMContext) -> None:
    if APP_CONFIG is None:
        await callback.answer("Конфиг не загружен", show_alert=True)
        return
    kb = _config_section_keyboard("price", APP_CONFIG.raw)
    await callback.message.edit_text("Параметры price_block:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "cfg_section_desc")
async def cfg_section_desc(callback: CallbackQuery, state: FSMContext) -> None:
    if APP_CONFIG is None:
        await callback.answer("Конфиг не загружен", show_alert=True)
        return
    kb = _config_section_keyboard("desc", APP_CONFIG.raw)
    await callback.message.edit_text("Параметры description_block:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("cfg_edit:"))
async def cfg_edit_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if APP_CONFIG is None:
        await callback.answer("Конфиг не загружен", show_alert=True)
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Некорректный параметр", show_alert=True)
        return
    _, section, key = parts
    section_data = _config_section_data(section, APP_CONFIG.raw)
    if key not in section_data:
        await callback.answer("Параметр не найден", show_alert=True)
        return
    await state.set_state(ConfigStates.waiting_for_value)
    await state.update_data(cfg_section=section, cfg_key=key)
    current = section_data[key]
    await callback.message.edit_text(
        f"Введите новое значение для `{section}.{key}`\nТекущее: `{current}`",
        reply_markup=cancel_keyboard(
            extra_buttons=[
                [InlineKeyboardButton(text="⬅️ К разделу", callback_data=f"cfg_section_{section}")]
            ]
        ),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(ConfigStates.waiting_for_value, F.text)
async def cfg_value_input_handler(message: Message, state: FSMContext) -> None:
    if APP_CONFIG is None:
        await message.answer("Конфиг не загружен.")
        return
    data = await state.get_data()
    section = data.get("cfg_section")
    key = data.get("cfg_key")
    if not section or not key:
        await state.clear()
        await message.answer("Не удалось определить параметр.", reply_markup=main_menu_keyboard())
        return
    section_data = _config_section_data(section, APP_CONFIG.raw)
    old_value = section_data[key]
    try:
        new_value = _convert_config_value(message.text, old_value)
    except ValueError as exc:
        await message.answer(f"Неверный формат значения: {exc}")
        return
    section_data[key] = new_value
    _save_config_to_file(APP_CONFIG.raw)
    await state.clear()
    kb = _config_section_keyboard(section, APP_CONFIG.raw)
    section_name = "output" if section == "output" else "price_block" if section == "price" else "description_block"
    await message.answer(
        f"Сохранено: `{section}.{key}` = `{new_value}`",
        parse_mode="Markdown",
    )
    await message.answer(f"Параметры {section_name}:", reply_markup=kb)


@router.message(ConfigStates.waiting_for_value)
async def cfg_value_wrong_input_handler(message: Message) -> None:
    await message.answer("Отправьте новое значение параметра текстом.")


@router.callback_query(CardStates.waiting_for_photos, F.data == "photos_done")
async def photos_done_callback(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    photo_file_ids = data.get("photo_file_ids", [])
    if len(photo_file_ids) < 1:
        await callback.answer("Нужно хотя бы одно фото.", show_alert=True)
        return
    await state.set_state(CardStates.waiting_for_features)
    await callback.message.edit_text(
        "Отправьте текстовые ХАРАКТЕРИСТИКИ товара (списком или абзацем).",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(CardStates.waiting_for_photos, F.photo)
async def collect_photo_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_file_ids = data.get("photo_file_ids", [])

    if len(photo_file_ids) >= 3:
        await message.answer(
            "Максимум 3 фото. Нажмите «Готово» ниже.",
            reply_markup=cancel_keyboard(
                extra_buttons=[
                    [InlineKeyboardButton(text="✅ Готово", callback_data="photos_done")]
                ]
            ),
        )
        return

    largest_photo = message.photo[-1]
    photo_file_ids.append(largest_photo.file_id)
    await state.update_data(photo_file_ids=photo_file_ids)
    await message.answer(
        f"Фото добавлено: {len(photo_file_ids)}/3",
        reply_markup=cancel_keyboard(
            extra_buttons=[
                [InlineKeyboardButton(text="✅ Готово", callback_data="photos_done")]
            ]
        ),
    )


@router.message(CardStates.waiting_for_photos)
async def wrong_photos_input_handler(message: Message) -> None:
    await message.answer("Отправьте фото или нажмите кнопку «Готово».")


@router.message(CardStates.waiting_for_features, F.text)
async def features_handler(message: Message, state: FSMContext) -> None:
    features = message.text.strip()
    if not features:
        await message.answer("Характеристики пустые. Отправьте текст.")
        return
    await state.update_data(features=features)
    await state.set_state(CardStates.waiting_for_description)
    await message.answer("Теперь отправьте ОПИСАНИЕ товара.", reply_markup=cancel_keyboard())


@router.message(CardStates.waiting_for_description, F.text)
async def description_handler(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    if not description:
        await message.answer("Описание пустое. Отправьте текст.")
        return
    await state.update_data(description=description)
    await state.set_state(CardStates.waiting_for_price)
    await message.answer("Отправьте цену (например: 12 990 ₽).", reply_markup=cancel_keyboard())


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
    photo_file_ids: list[str] = data.get("photo_file_ids", [])
    features: str = data.get("features", "")
    description: str = data.get("description", "")

    await message.answer("Собираю карточку, подождите...")

    try:
        if APP_CONFIG is None:
            raise RuntimeError("Config not loaded")
        photo_bytes_list = await download_photos(bot, photo_file_ids)
        output_file = await build_card(
            config=APP_CONFIG,
            photos=photo_bytes_list,
            features=features,
            description=description,
            price=price_text,
            user_id=message.from_user.id if message.from_user else 0,
        )
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка при создании карточки: {exc}")
        return

    buffered_file = BufferedInputFile(
        output_file.read_bytes(),
        filename=output_file.name,
    )
    await message.answer_photo(buffered_file, caption="Готово. Карточка для Авито создана.")
    output_file.unlink(missing_ok=True)
    await state.clear()
    try:
        output_file.unlink(missing_ok=True)
    except OSError:
        pass


@router.message(CardStates.waiting_for_price)
async def wrong_price_input_handler(message: Message) -> None:
    await message.answer("Отправьте цену текстом.")


async def download_photos(bot: Bot, file_ids: list[str]) -> list[bytes]:
    result: list[bytes] = []
    for file_id in file_ids:
        file = await bot.get_file(file_id)
        buffer = BytesIO()
        await bot.download_file(file.file_path, destination=buffer)
        result.append(buffer.getvalue())
    return result


def to_data_url(photo_bytes: bytes) -> str:
    b64 = base64.b64encode(photo_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def build_html(config: dict[str, Any], photos: list[bytes], features: str, description: str, price: str) -> str:
    output_cfg = config["output"]
    cards_cfg = config["cards"]
    price_cfg = cards_cfg["price_block"]
    desc_cfg = cards_cfg["description_block"]

    width = int(output_cfg["width"])
    height = int(output_cfg["height"])
    padding = int(output_cfg["padding"])
    gap = int(output_cfg["gap"])
    photo_gap = int(output_cfg.get("photo_gap", gap))
    bg_color = output_cfg["background_color"]
    grid_radius = int(output_cfg["photo_grid_border_radius"])
    left_ratio = float(output_cfg.get("left_column_ratio", 0.5))

    safe_features = html.escape(features).replace("\n", "<br/>")
    safe_description = html.escape(description).replace("\n", "<br/>")
    safe_price = html.escape(price)
    n = len(photos)

    # Одна картинка на ячейку, обрезка по размеру (object-fit: cover), без дублирования
    def img_cell(data_url: str) -> str:
        return f'<div class="cell"><img src="{data_url}" alt="" /></div>'

    # 1 фото — 4 экземпляра друг под другом; 2 — две ячейки поровну; 3 — сверху 50%, снизу две по 50% слева и справа
    if n == 1:
        u = to_data_url(photos[0])
        photo_area = f'''
    <div class="photo-area photo-area-1">
      {img_cell(u)}
      {img_cell(u)}
      {img_cell(u)}
      {img_cell(u)}
    </div>'''
    elif n == 2:
        u1, u2 = to_data_url(photos[0]), to_data_url(photos[1])
        photo_area = f'''
    <div class="photo-area photo-area-2">
      {img_cell(u1)}
      {img_cell(u2)}
      {img_cell(u1)}
      {img_cell(u2)}
    </div>'''
    else:
        u1, u2, u3 = to_data_url(photos[0]), to_data_url(photos[1]), to_data_url(photos[2])
        photo_area = f'''
    <div class="photo-area photo-area-3">
      {img_cell(u1)}
      <div class="bottom-row">
        {img_cell(u2)}
        {img_cell(u3)}
      </div>
    </div>'''

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <style>
    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      width: {width}px;
      height: {height}px;
      font-family: Arial, Helvetica, sans-serif;
      background: transparent;
    }}

    #card {{
      width: 100%;
      height: 100%;
      background: {bg_color};
      display: flex;
      padding: {padding}px;
      gap: {gap}px;
    }}

    .left {{
      flex: 0 0 {left_ratio * 100}%;
      width: {left_ratio * 100}%;
      min-width: 0;
      display: flex;
      flex-direction: column;
      border-radius: {grid_radius}px;
      overflow: hidden;
    }}

    .right {{
      flex: 0 0 {(1 - left_ratio) * 100}%;
      width: {(1 - left_ratio) * 100}%;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: {gap}px;
    }}

    .photo-area {{
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: {photo_gap}px;
      min-height: 0;
    }}

    .photo-area-1 .cell {{
      flex: 1;
      min-height: 0;
    }}

    .photo-area-2 .cell {{
      flex: 1;
      min-height: 0;
    }}

    .photo-area-3 {{
      gap: {photo_gap}px;
    }}

    .photo-area-3 > .cell:first-child {{
      flex: 0 0 50%;
      min-height: 0;
    }}

    .photo-area-3 .bottom-row {{
      flex: 0 0 50%;
      display: flex;
      gap: {photo_gap}px;
      min-height: 0;
    }}

    .photo-area-3 .bottom-row .cell {{
      flex: 1;
      min-width: 0;
    }}

    .cell {{
      overflow: hidden;
      background: #ddd;
    }}

    .cell img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center;
      display: block;
    }}

    .info {{
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
      gap: {photo_gap}px;
    }}

    .info-block {{
      flex: 1;
      min-height: 0;
      border: {desc_cfg["border"]};
      border-radius: {int(desc_cfg["border_radius"])}px;
      background: {desc_cfg["background_color"]};
      color: {desc_cfg["text_color"]};
      padding: {desc_cfg["padding"]};
      overflow: auto;
    }}

    .info-title {{
      font-size: {int(desc_cfg["font_size"])}px;
      font-weight: 900;
      margin-bottom: 4px;
    }}

    .info-text {{
      font-size: {int(desc_cfg["font_size"])}px;
      line-height: {float(desc_cfg["line_height"])};
      font-weight: 700;
      white-space: normal;
    }}

    .price {{
      flex-shrink: 0;
      padding: {price_cfg["padding"]};
      border: {price_cfg["border"]};
      border-radius: {int(price_cfg["border_radius"])}px;
      background: {price_cfg["background_color"]};
      color: {price_cfg["text_color"]};
      font-size: {int(price_cfg["font_size"])}px;
      font-weight: 900;
      line-height: 1;
      -webkit-text-stroke: {int(price_cfg["text_stroke_width"])}px {price_cfg["text_stroke_color"]};
      text-shadow: 0 0 1px {price_cfg["text_stroke_color"]};
    }}
  </style>
</head>
<body>
  <div id="card">
    <div class="left">{photo_area}
    </div>
    <div class="right">
      <div class="info">
        <div class="info-block">
          <div class="info-title">Характеристики</div>
          <div class="info-text">{safe_features}</div>
        </div>
        <div class="info-block">
          <div class="info-title">Описание</div>
          <div class="info-text">{safe_description}</div>
        </div>
      </div>
      <div class="price">{safe_price}</div>
    </div>
  </div>
</body>
</html>
"""


async def render_png(html_content: str, width: int, height: int, output_path: Path) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": height})
        await page.set_content(html_content, wait_until="networkidle")
        card = page.locator("#card")
        await card.screenshot(path=str(output_path))
        await browser.close()


async def build_card(
    config: AppConfig,
    photos: list[bytes],
    features: str,
    description: str,
    price: str,
    user_id: int,
) -> Path:
    html_content = build_html(config.raw, photos, features, description, price)
    width = int(config.raw["output"]["width"])
    height = int(config.raw["output"]["height"])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"card_{user_id}_{ts}.png"
    await render_png(html_content, width, height, output_path)
    return output_path


async def run() -> None:
    global APP_CONFIG
    app_config = AppConfig.load(BASE_DIR / "config.json", BASE_DIR / ".env")
    APP_CONFIG = app_config
    bot = Bot(token=app_config.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
