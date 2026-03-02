import json
from typing import Any

from .constants import BASE_DIR


EXAMPLES_PATH = BASE_DIR / "examples.json"


def load_examples() -> dict[str, Any]:
    """Загружает сохранённые данные примера (фото и тексты) из файла, если он есть."""
    if not EXAMPLES_PATH.exists():
        return {}
    try:
        raw = EXAMPLES_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_examples(data: dict[str, Any]) -> None:
    """Сохраняет данные примера в JSON, чтобы переживали перезапуск бота/контейнера."""
    try:
        EXAMPLES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Логирование не обязательно; пропускаем сбой сохранения, чтобы не ломать бота.
        pass

