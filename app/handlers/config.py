from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from ..config_store import convert_config_value, save_config
from ..context import get_app_config
from ..states import ConfigStates
from ..ui import cancel_keyboard, config_section_data, config_section_keyboard, main_menu_keyboard


router = Router()


@router.callback_query(F.data == "cfg_section_output")
async def cfg_section_output(callback: CallbackQuery, state: FSMContext) -> None:
    _ = state
    kb = config_section_keyboard("output", get_app_config().raw)
    await callback.message.edit_text("Параметры output:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "cfg_section_price")
async def cfg_section_price(callback: CallbackQuery, state: FSMContext) -> None:
    _ = state
    kb = config_section_keyboard("price", get_app_config().raw)
    await callback.message.edit_text("Параметры блока «Название-цена»:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "cfg_section_desc")
async def cfg_section_desc(callback: CallbackQuery, state: FSMContext) -> None:
    _ = state
    kb = config_section_keyboard("desc", get_app_config().raw)
    await callback.message.edit_text("Параметры description_block:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("cfg_edit:"))
async def cfg_edit_handler(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Некорректный параметр", show_alert=True)
        return
    _, section, key = parts
    section_data = config_section_data(section, get_app_config().raw)
    if key not in section_data:
        await callback.answer("Параметр не найден", show_alert=True)
        return
    await state.set_state(ConfigStates.waiting_for_value)
    await state.update_data(cfg_section=section, cfg_key=key)
    current = section_data[key]
    await callback.message.edit_text(
        f"Введите новое значение для `{section}.{key}`\nТекущее: `{current}`",
        reply_markup=cancel_keyboard(extra_buttons=[[InlineKeyboardButton(text="⬅️ К разделу", callback_data=f"cfg_section_{section}")]]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(ConfigStates.waiting_for_value, F.text)
async def cfg_value_input_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    section = data.get("cfg_section")
    key = data.get("cfg_key")
    if not section or not key:
        await state.clear()
        await message.answer("Не удалось определить параметр.", reply_markup=main_menu_keyboard())
        return
    cfg = get_app_config().raw
    section_data = config_section_data(section, cfg)
    old_value = section_data[key]
    try:
        new_value = convert_config_value(message.text, old_value)
    except ValueError as exc:
        await message.answer(f"Неверный формат значения: {exc}")
        return
    section_data[key] = new_value
    save_config(cfg)
    await state.clear()
    await message.answer(f"Сохранено: `{section}.{key}` = `{new_value}`", parse_mode="Markdown")
    kb = config_section_keyboard(section, cfg)
    section_name = "output" if section == "output" else "price_block" if section == "price" else "description_block"
    await message.answer(f"Параметры {section_name}:", reply_markup=kb)


@router.message(ConfigStates.waiting_for_value)
async def cfg_value_wrong_input_handler(message: Message) -> None:
    await message.answer("Отправьте новое значение параметра текстом.")

