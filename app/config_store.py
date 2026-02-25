import json
from typing import Any

from .constants import BASE_DIR


def convert_config_value(raw_value: str, old_value: Any) -> Any:
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


def save_config(raw: dict[str, Any]) -> None:
    (BASE_DIR / "config.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

