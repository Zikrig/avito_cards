from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..auth_store import (
    get_role,
    list_users_and_admins,
    remove_user,
    update_description_template,
    update_usage_instructions,
    ensure_user_role,
    list_admin_requests,
    pop_admin_request,
    create_invite,
    list_invites,
)
from ..logo_store import load_logos, set_shop_logo
from ..states import AdminEditStates, LogoConfigStates
from ..ui import cancel_keyboard, main_menu_keyboard


router = Router()


def _ensure_min_role(user_id: int, min_role: str) -> bool:
    order = {"guest": 0, "user": 1, "admin": 2, "root_admin": 3}
    role = get_role(user_id)
    return order.get(role, 0) >= order.get(min_role, 0)


@router.callback_query(F.data == "menu_usage")
async def menu_usage(callback: CallbackQuery, state: FSMContext) -> None:
    from ..auth_store import load_auth

    _ = state
    usage = load_auth().usage_instructions
    await callback.message.edit_text(usage, reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_edit_usage")
async def admin_edit_usage(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    await state.set_state(AdminEditStates.waiting_for_usage)
    await callback.message.edit_text(
        "Отправьте новый текст инструкции по использованию бота одним сообщением.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_edit_desc_template")
async def admin_edit_desc_template(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    await state.set_state(AdminEditStates.waiting_for_desc_template)
    await callback.message.edit_text(
        "Отправьте новый шаблон описания (текст блока слева). Он будет использоваться по умолчанию.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_logos")
async def admin_logos(callback: CallbackQuery, state: FSMContext) -> None:
    """Меню конфигуратора логотипов: до трёх магазинов, только для администраторов."""
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state
    shops = load_logos()
    rows: list[list[InlineKeyboardButton]] = []
    for shop in shops:
        mark = " ✅" if shop.logo_file_id else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{shop.title}{mark}",
                    callback_data=f"admin_logo_shop:{shop.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text(
        "Выберите магазин, для которого нужно задать или обновить логотип.\n"
        "Всего поддерживается до 3 магазинов. Логотипы используются при генерации карточек.",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_logo_shop:"))
async def admin_logo_shop(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор конкретного магазина для загрузки логотипа."""
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    parts = (callback.data or "").split(":", 1)
    if len(parts) != 2:
        await callback.answer("Некорректный магазин.", show_alert=True)
        return
    try:
        shop_id = int(parts[1])
    except ValueError:
        await callback.answer("Некорректный магазин.", show_alert=True)
        return
    shops = load_logos()
    title = next((s.title for s in shops if s.id == shop_id), f"Магазин {shop_id}")
    await state.set_state(LogoConfigStates.waiting_for_logo)
    await state.update_data(admin_logo_shop_id=shop_id)
    await callback.message.edit_text(
        f"Отправьте изображение логотипа для «{title}» одним файлом (фото или документ PNG/JPG).",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(LogoConfigStates.waiting_for_logo, F.photo)
async def admin_logo_photo(message: Message, state: FSMContext) -> None:
    """Сохранение логотипа магазина из фото."""
    data = await state.get_data()
    shop_id = int(data.get("admin_logo_shop_id") or 0)
    if not shop_id:
        await message.answer("Не удалось определить магазин. Начните с меню конфигуратора логотипов.")
        await state.clear()
        return
    user_id = message.from_user.id if message.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await message.answer("Недостаточно прав для изменения.")
        await state.clear()
        return
    file_id = message.photo[-1].file_id
    set_shop_logo(shop_id, file_id)
    await state.clear()
    role = get_role(user_id)
    await message.answer("Логотип магазина сохранён.", reply_markup=main_menu_keyboard(role))


@router.message(LogoConfigStates.waiting_for_logo, F.document)
async def admin_logo_document(message: Message, state: FSMContext) -> None:
    """Сохранение логотипа магазина из документа-изображения."""
    data = await state.get_data()
    shop_id = int(data.get("admin_logo_shop_id") or 0)
    if not shop_id:
        await message.answer("Не удалось определить магазин. Начните с меню конфигуратора логотипов.")
        await state.clear()
        return
    user_id = message.from_user.id if message.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await message.answer("Недостаточно прав для изменения.")
        await state.clear()
        return
    doc = message.document
    if not (doc and doc.mime_type and doc.mime_type.startswith("image/")):
        await message.answer("Отправьте файл-изображение (PNG, JPG и т.п.) или выйдите в меню.")
        return
    set_shop_logo(shop_id, doc.file_id)
    await state.clear()
    role = get_role(user_id)
    await message.answer("Логотип магазина сохранён.", reply_markup=main_menu_keyboard(role))


@router.message(AdminEditStates.waiting_for_usage, F.text)
async def admin_usage_input(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await message.answer("Недостаточно прав для изменения.")
        await state.clear()
        return
    text = message.text.strip()
    if not text:
        await message.answer("Текст пустой, отправьте непустое сообщение.")
        return
    update_usage_instructions(text)
    await message.answer("Инструкция обновлена.")
    await state.clear()
    role = get_role(user_id)
    await message.answer("Главное меню. Выберите действие:", reply_markup=main_menu_keyboard(role))


@router.message(AdminEditStates.waiting_for_desc_template, F.text)
async def admin_desc_template_input(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await message.answer("Недостаточно прав для изменения.")
        await state.clear()
        return
    text = message.text.strip()
    if not text:
        await message.answer("Текст пустой, отправьте непустое сообщение.")
        return
    update_description_template(text)
    await message.answer("Шаблон описания обновлён.")
    await state.clear()
    role = get_role(user_id)
    await message.answer("Главное меню. Выберите действие:", reply_markup=main_menu_keyboard(role))


@router.callback_query(F.data == "root_admin_users")
async def root_admin_users(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "root_admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state
    users, admins = list_users_and_admins()
    requests = list_admin_requests()

    lines: list[str] = []
    lines.append("Администраторы:")
    if admins:
        for uid in sorted(admins):
            lines.append(f"{uid} — ⭐ админ")
    else:
        lines.append("— нет администраторов в auth.json —")

    # Пользователи без админских прав (auth.users \ admins)
    plain_users = sorted(u for u in users if u not in admins)

    lines.append("")
    lines.append("Пользователи:")
    if plain_users:
        for uid in plain_users:
            lines.append(f"{uid} — 👤 пользователь")
    else:
        lines.append("— нет зарегистрированных пользователей —")
    if users:
        for uid in sorted(users):
            role_mark = "⭐ админ" if uid in admins else "👤 пользователь"
            lines.append(f"{uid} — {role_mark}")
    else:
        lines.append("— нет зарегистрированных пользователей —")

    lines.append("")
    if requests:
        lines.append("Заявки на администратора:")
        for uid, name in requests.items():
            lines.append(f"{uid} — {name}")
    else:
        lines.append("Заявок на администратора нет.")

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    # Кнопки для обработки заявок (одобрить / отклонить)
    for uid in requests.keys():
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ Одобрить {uid}", callback_data=f"root_admin_approve:{uid}:admin"
                ),
                InlineKeyboardButton(
                    text="🚫 Отклонить", callback_data=f"root_admin_approve:{uid}:reject"
                ),
            ]
        )

    # Кнопки для выбора пользователя и управления ролями
    for uid in sorted(users | admins):
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"⚙️ {uid}", callback_data=f"root_admin_user_menu:{uid}"
                )
            ]
        )

    keyboard_rows.append(
        [InlineKeyboardButton(text="Обновить список", callback_data="root_admin_users")]
    )
    keyboard_rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="cancel")])

    kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "root_admin_invites")
async def root_admin_invites(callback: CallbackQuery, state: FSMContext) -> None:
    """Просмотр и создание инвайт‑ссылок (токенов) для входа пользователей."""
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "root_admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state

    invites = list_invites()
    lines: list[str] = []
    if invites:
        lines.append("Текущие инвайт‑токены:")
        for token, label in invites.items():
            label_part = f" — {label}" if label else ""
            # Показываем токен как есть; root‑админ может собрать ссылку вида:
            # https://t.me/<имя_бота>?start=<token>
            lines.append(f"{token}{label_part}")
    else:
        lines.append("Инвайт‑токенов пока нет.")
    lines.append("")
    lines.append(
        "Инвайт‑токен используется один раз при переходе по deep‑link /start <token> "
        "и автоматически регистрирует пользователя."
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать инвайт‑токен", callback_data="root_admin_invite_new")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="cancel")],
        ]
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "root_admin_invite_new")
async def root_admin_invite_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Создание нового инвайт‑токена без подписи."""
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "root_admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state

    token = create_invite()
    invites = list_invites()

    lines: list[str] = []
    lines.append(f"Создан новый инвайт‑токен: {token}")
    lines.append("")
    lines.append("Текущие инвайт‑токены:")
    for t, label in invites.items():
        label_part = f" — {label}" if label else ""
        lines.append(f"{t}{label_part}")
    lines.append("")
    lines.append(
        "Инвайт‑токен используется один раз при переходе по deep‑link /start <token> "
        "и автоматически регистрирует пользователя."
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать ещё", callback_data="root_admin_invite_new")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="cancel")],
        ]
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data.startswith("root_admin_approve:"))
async def root_admin_approve(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state
    _, target_id_str, decision = (callback.data or "").split(":", 2)
    try:
        target_id = int(target_id_str)
    except ValueError:
        await callback.answer("Некорректный ID.", show_alert=True)
        return
    reason = pop_admin_request(target_id)
    if reason is None:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    if decision == "admin":
        ensure_user_role(target_id, as_admin=True)
        await callback.answer("Пользователь назначен администратором.", show_alert=True)
        # Уведомим пользователя о результате
        try:
            await callback.bot.send_message(
                chat_id=target_id,
                text="Ваша заявка на роль администратора одобрена.",
            )
        except Exception:
            pass
    else:
        await callback.answer("Заявка отклонена.", show_alert=True)
        # Уведомим пользователя об отклонении
        try:
            await callback.bot.send_message(
                chat_id=target_id,
                text="Ваша заявка на роль администратора отклонена.",
            )
        except Exception:
            pass
    # Обновим список
    await root_admin_users(callback, state)


@router.callback_query(F.data.startswith("root_admin_user_menu:"))
async def root_admin_user_menu(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "root_admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state
    _, target_id_str = (callback.data or "").split(":", 1)
    try:
        target_id = int(target_id_str)
    except ValueError:
        await callback.answer("Некорректный ID.", show_alert=True)
        return
    users, admins = list_users_and_admins()
    if target_id not in users and target_id not in admins:
        await callback.answer("Пользователь не найден в auth.json.", show_alert=True)
        return
    is_admin = target_id in admins
    role_text = "администратор" if is_admin else "пользователь"
    text = f"Управление пользователем {target_id} (текущая роль: {role_text})."

    buttons: list[list[InlineKeyboardButton]] = []
    if not is_admin:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Сделать администратором",
                    callback_data=f"root_admin_user_set_admin:{target_id}",
                )
            ]
        )
    if is_admin:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Сделать пользователем",
                    callback_data=f"root_admin_user_set_user:{target_id}",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🗑 Удалить пользователя", callback_data=f"root_admin_user_delete:{target_id}"
            )
        ]
    )
    buttons.append(
        [InlineKeyboardButton(text="⬅️ К списку", callback_data="root_admin_users")]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("root_admin_user_set_admin:"))
async def root_admin_user_set_admin(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "root_admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state
    _, target_id_str = (callback.data or "").split(":", 1)
    try:
        target_id = int(target_id_str)
    except ValueError:
        await callback.answer("Некорректный ID.", show_alert=True)
        return
    ensure_user_role(target_id, as_admin=True)
    await callback.answer("Роль пользователя обновлена: администратор.", show_alert=True)
    # Сообщим пользователю, кем он назначен
    try:
        await callback.bot.send_message(
            chat_id=target_id,
            text="Ваша роль в боте изменена: теперь вы администратор.",
        )
    except Exception:
        pass
    await root_admin_user_menu(callback, state)


@router.callback_query(F.data.startswith("root_admin_user_set_user:"))
async def root_admin_user_set_user(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "root_admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state
    _, target_id_str = (callback.data or "").split(":", 1)
    try:
        target_id = int(target_id_str)
    except ValueError:
        await callback.answer("Некорректный ID.", show_alert=True)
        return
    ensure_user_role(target_id, as_admin=False)
    await callback.answer("Роль пользователя обновлена: пользователь.", show_alert=True)
    # Сообщим пользователю, кем он назначен
    try:
        await callback.bot.send_message(
            chat_id=target_id,
            text="Ваша роль в боте изменена: теперь вы обычный пользователь.",
        )
    except Exception:
        pass
    await root_admin_user_menu(callback, state)


@router.callback_query(F.data.startswith("root_admin_user_delete:"))
async def root_admin_user_delete(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not _ensure_min_role(user_id, "root_admin"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    _ = state
    _, target_id_str = (callback.data or "").split(":", 1)
    try:
        target_id = int(target_id_str)
    except ValueError:
        await callback.answer("Некорректный ID.", show_alert=True)
        return
    # Попробуем уведомить пользователя до фактического удаления
    try:
        await callback.bot.send_message(
            chat_id=target_id,
            text="Ваша учётная запись в боте была удалена администратором.",
        )
    except Exception:
        pass
    remove_user(target_id)
    await callback.answer("Пользователь удалён.", show_alert=True)
    await root_admin_users(callback, state)

