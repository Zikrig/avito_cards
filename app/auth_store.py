import json
import secrets
from dataclasses import dataclass
from typing import Any

from .constants import DATA_DIR
from .context import get_app_config


AUTH_PATH = DATA_DIR / "auth.json"


@dataclass
class AuthData:
    users: set[int]
    admins: set[int]
    usage_instructions: str
    description_template: str
    pending_admin_requests: dict[int, str]


def _load_raw() -> dict[str, Any]:
    if not AUTH_PATH.exists():
        return {}
    try:
        raw = AUTH_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_raw(data: dict[str, Any]) -> None:
    try:
        AUTH_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_auth() -> AuthData:
    data = _load_raw()
    users = {int(x) for x in data.get("users", []) if isinstance(x, int) or isinstance(x, str)}
    admins = {int(x) for x in data.get("admins", []) if isinstance(x, int) or isinstance(x, str)}

    usage_instructions = str(
        data.get(
            "usage_instructions",
            "Этот бот собирает карточки для объявлений на Авито из 3 фото, характеристик и описания.",
        )
    )
    DEFAULT_DESCRIPTION_TEMPLATE = (
        "Это решение подойдёт не только геймерам, но и дизайнерам, стримерам, 3D-моделлерам и видеомонтажёрам."
    )
    description_template = str(data.get("description_template", DEFAULT_DESCRIPTION_TEMPLATE))
    pending_raw = data.get("pending_admin_requests", {})
    pending_admin_requests: dict[int, str] = {}
    if isinstance(pending_raw, dict):
        for k, v in pending_raw.items():
            try:
                uid = int(k)
            except (TypeError, ValueError):
                continue
            pending_admin_requests[uid] = str(v)
    # нормализуем и сохраняем
    data.setdefault("users", list(users))
    data.setdefault("admins", list(admins))
    data["usage_instructions"] = usage_instructions
    data["description_template"] = description_template
    data["pending_admin_requests"] = {str(k): v for k, v in pending_admin_requests.items()}
    _save_raw(data)

    return AuthData(
        users=users,
        admins=admins,
        usage_instructions=usage_instructions,
        description_template=description_template,
        pending_admin_requests=pending_admin_requests,
    )


def save_auth(auth: AuthData) -> None:
    data = {
        "users": sorted(auth.users),
        "admins": sorted(auth.admins),
        "usage_instructions": auth.usage_instructions,
        "description_template": auth.description_template,
        "pending_admin_requests": {str(k): v for k, v in auth.pending_admin_requests.items()},
    }
    _save_raw(data)


def get_role(user_id: int) -> str:
    """
    Возвращает роль пользователя:
    - "root_admin" — пользователь из ADMIN_IDS (имеет все права)
    - "admin" — администратор (может править инструкции и шаблон описания)
    - "user" — обычный пользователь (может генерировать карточки)
    - "guest" — не зарегистрирован (бот отвечает «Это служебный бот»)
    """
    cfg = get_app_config()
    if user_id in cfg.admin_ids:
        return "root_admin"
    auth = load_auth()
    if user_id in auth.admins:
        return "admin"
    if user_id in auth.users:
        return "user"
    return "guest"


def ensure_user_role(user_id: int, as_admin: bool) -> None:
    auth = load_auth()
    if as_admin:
        auth.admins.add(user_id)
        auth.users.discard(user_id)
    else:
        auth.users.add(user_id)
        auth.admins.discard(user_id)
    save_auth(auth)


def remove_user(user_id: int) -> None:
    auth = load_auth()
    auth.users.discard(user_id)
    auth.admins.discard(user_id)
     # также на всякий случай очищаем возможную заявку
    auth.pending_admin_requests.pop(user_id, None)
    save_auth(auth)


def update_usage_instructions(text: str) -> None:
    auth = load_auth()
    auth.usage_instructions = text.strip()
    save_auth(auth)


def update_description_template(text: str) -> None:
    auth = load_auth()
    auth.description_template = text.strip()
    save_auth(auth)


def list_users_and_admins() -> tuple[set[int], set[int]]:
    auth = load_auth()
    return auth.users, auth.admins


def add_admin_request(user_id: int, username: str) -> None:
    auth = load_auth()
    auth.pending_admin_requests[user_id] = username
    save_auth(auth)


def pop_admin_request(user_id: int) -> str | None:
    auth = load_auth()
    reason = auth.pending_admin_requests.pop(user_id, None)
    save_auth(auth)
    return reason


def list_admin_requests() -> dict[int, str]:
    auth = load_auth()
    return dict(auth.pending_admin_requests)

