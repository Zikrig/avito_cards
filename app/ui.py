from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧩 Создать карточку", callback_data="menu_create_card")],
            [InlineKeyboardButton(text="🖼 Примеры", callback_data="menu_examples")],
            [InlineKeyboardButton(text="⚙️ Настройки конфигурации", callback_data="menu_config")],
        ]
    )


def cancel_keyboard(
    extra_buttons: list[list[InlineKeyboardButton]] | None = None,
    default_callback: str | None = None,
) -> InlineKeyboardMarkup:
    rows = extra_buttons[:] if extra_buttons else []
    if default_callback:
        rows.append([InlineKeyboardButton(text="По умолчанию", callback_data=default_callback)])
    rows.append([InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def examples_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="КнВ", callback_data="example_gen:1"),
                InlineKeyboardButton(text="МНСГ", callback_data="example_gen:2"),
                InlineKeyboardButton(text="Паша", callback_data="example_gen:3"),
            ],
            [InlineKeyboardButton(text="🧾 Задать данные (3 фото)", callback_data="example_edit_data")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel")],
        ]
    )


def template_select_keyboard(prefix: str = "card_tpl") -> InlineKeyboardMarkup:
    """Клавиатура выбора варианта SVG-шаблона (КнВ, МНСГ, Паша)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="КнВ", callback_data=f"{prefix}:1")],
            [InlineKeyboardButton(text="МНСГ", callback_data=f"{prefix}:2")],
            [InlineKeyboardButton(text="Паша", callback_data=f"{prefix}:3")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel")],
        ]
    )

def example_builder_keyboard(data: dict[str, Any]) -> InlineKeyboardMarkup:
    photo_count = len(data.get("example_photo_file_ids", []))
    photos_label = f"📷 Фото: главное + 2 доп. ({photo_count}/3)"
    has_logo = bool(data.get("example_logo_file_id"))
    logo_label = "🖼 Логотип" + (" ✅" if has_logo else "")
    has_texts = bool(data.get("title_main"))
    texts_label = "📝 Заполнить тексты (название, цена, характеристики)" + (" ✅" if has_texts else "")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=photos_label, callback_data="example_edit_photos")],
            [InlineKeyboardButton(text=logo_label, callback_data="example_edit_logo")],
            [InlineKeyboardButton(text=texts_label, callback_data="example_edit_texts")],
            [InlineKeyboardButton(text="⬅️ К примерам", callback_data="menu_examples")],
        ]
    )


def config_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📐 Размеры и фон", callback_data="cfg_section_output")],
            [InlineKeyboardButton(text="💰 Название-цена", callback_data="cfg_section_price")],
            [InlineKeyboardButton(text="📝 Описание", callback_data="cfg_section_desc")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel")],
        ]
    )


def config_section_keyboard(section: str, raw: dict[str, Any]) -> InlineKeyboardMarkup:
    if section == "output":
        cfg = raw["output"]
        rows = [
            [InlineKeyboardButton(text=f"width: {cfg['width']}", callback_data="cfg_edit:output:width")],
            [InlineKeyboardButton(text=f"height: {cfg['height']}", callback_data="cfg_edit:output:height")],
            [InlineKeyboardButton(text=f"background_color: {cfg['background_color']}", callback_data="cfg_edit:output:background_color")],
            [InlineKeyboardButton(text=f"font_family: {cfg.get('font_family', 'Arial, Helvetica, sans-serif')}", callback_data="cfg_edit:output:font_family")],
            [InlineKeyboardButton(text=f"padding: {cfg['padding']}", callback_data="cfg_edit:output:padding")],
            [InlineKeyboardButton(text=f"gap: {cfg['gap']}", callback_data="cfg_edit:output:gap")],
            [InlineKeyboardButton(text=f"photo_gap: {cfg['photo_gap']}", callback_data="cfg_edit:output:photo_gap")],
            [InlineKeyboardButton(text=f"left_column_ratio: {cfg['left_column_ratio']}", callback_data="cfg_edit:output:left_column_ratio")],
        ]
    elif section == "price":
        cfg = raw["cards"]["price_block"]
        rows = [
            [InlineKeyboardButton(text=f"title: {cfg.get('title', 'Название-цена')}", callback_data="cfg_edit:price:title")],
            [InlineKeyboardButton(text=f"background_color: {cfg['background_color']}", callback_data="cfg_edit:price:background_color")],
            [InlineKeyboardButton(text=f"text_color: {cfg['text_color']}", callback_data="cfg_edit:price:text_color")],
            [InlineKeyboardButton(text=f"font_family: {cfg.get('font_family', 'Arial, Helvetica, sans-serif')}", callback_data="cfg_edit:price:font_family")],
            [InlineKeyboardButton(text=f"font_size: {cfg['font_size']}", callback_data="cfg_edit:price:font_size")],
            [InlineKeyboardButton(text=f"padding: {cfg['padding']}", callback_data="cfg_edit:price:padding")],
            [InlineKeyboardButton(text=f"border: {cfg['border']}", callback_data="cfg_edit:price:border")],
            [InlineKeyboardButton(text=f"border_radius: {cfg['border_radius']}", callback_data="cfg_edit:price:border_radius")],
            [InlineKeyboardButton(text=f"text_stroke_width: {cfg['text_stroke_width']}", callback_data="cfg_edit:price:text_stroke_width")],
            [InlineKeyboardButton(text=f"text_stroke_color: {cfg['text_stroke_color']}", callback_data="cfg_edit:price:text_stroke_color")],
        ]
    else:
        cfg = raw["cards"]["description_block"]
        rows = [
            [InlineKeyboardButton(text=f"features_title: {cfg.get('features_title', 'Характеристики')}", callback_data="cfg_edit:desc:features_title")],
            [InlineKeyboardButton(text=f"description_title: {cfg.get('description_title', 'Описание')}", callback_data="cfg_edit:desc:description_title")],
            [InlineKeyboardButton(text=f"background_color: {cfg['background_color']}", callback_data="cfg_edit:desc:background_color")],
            [InlineKeyboardButton(text=f"text_color: {cfg['text_color']}", callback_data="cfg_edit:desc:text_color")],
            [InlineKeyboardButton(text=f"font_family: {cfg.get('font_family', 'Arial, Helvetica, sans-serif')}", callback_data="cfg_edit:desc:font_family")],
            [InlineKeyboardButton(text=f"title_font_size: {cfg.get('title_font_size', cfg['font_size'])}", callback_data="cfg_edit:desc:title_font_size")],
            [InlineKeyboardButton(text=f"font_size: {cfg['font_size']}", callback_data="cfg_edit:desc:font_size")],
            [InlineKeyboardButton(text=f"line_height: {cfg['line_height']}", callback_data="cfg_edit:desc:line_height")],
            [InlineKeyboardButton(text=f"padding: {cfg['padding']}", callback_data="cfg_edit:desc:padding")],
            [InlineKeyboardButton(text=f"border: {cfg['border']}", callback_data="cfg_edit:desc:border")],
            [InlineKeyboardButton(text=f"border_radius: {cfg['border_radius']}", callback_data="cfg_edit:desc:border_radius")],
        ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_config")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def config_section_data(section: str, raw: dict[str, Any]) -> dict[str, Any]:
    if section == "output":
        return raw["output"]
    if section == "price":
        return raw["cards"]["price_block"]
    return raw["cards"]["description_block"]

