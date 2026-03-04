import json
from dataclasses import dataclass
from typing import Any

from .constants import DATA_DIR


LOGOS_PATH = DATA_DIR / "logos.json"


@dataclass
class ShopLogo:
    id: int
    title: str
    logo_file_id: str | None = None


def _load_raw() -> dict[str, Any]:
    if not LOGOS_PATH.exists():
        return {}
    try:
        raw = LOGOS_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_raw(data: dict[str, Any]) -> None:
    try:
        LOGOS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Не ломаем бота из-за ошибки сохранения.
        pass


def load_logos() -> list[ShopLogo]:
    """
    Возвращает до трёх магазинов с логотипами из logos.json.
    Если файл ещё не создан — заполняет заготовкой Магазин 1/2/3.
    """
    data = _load_raw()
    shops_raw = data.get("shops")
    shops: list[ShopLogo] = []
    if isinstance(shops_raw, list):
        for idx, item in enumerate(shops_raw, start=1):
            if not isinstance(item, dict):
                continue
            shop_id = int(item.get("id") or idx)
            title = str(item.get("title") or f"Магазин {shop_id}")
            logo_file_id = item.get("logo_file_id")
            if logo_file_id is not None:
                logo_file_id = str(logo_file_id)
            shops.append(ShopLogo(id=shop_id, title=title, logo_file_id=logo_file_id))
    if not shops:
        shops = [
            ShopLogo(id=1, title="Магазин 1"),
            ShopLogo(id=2, title="Магазин 2"),
            ShopLogo(id=3, title="Магазин 3"),
        ]
        save_logos(shops)
    return shops[:3]


def save_logos(shops: list[ShopLogo]) -> None:
    data = {
        "shops": [
            {
                "id": shop.id,
                "title": shop.title,
                "logo_file_id": shop.logo_file_id,
            }
            for shop in shops
        ]
    }
    _save_raw(data)


def set_shop_logo(shop_id: int, logo_file_id: str) -> None:
    """
    Обновляет логотип магазина по id. Если магазина с таким id нет — добавляет/расширяет список.
    """
    shops = load_logos()
    updated = False
    for shop in shops:
        if shop.id == shop_id:
            shop.logo_file_id = logo_file_id
            updated = True
            break
    if not updated:
        shops.append(ShopLogo(id=shop_id, title=f"Магазин {shop_id}", logo_file_id=logo_file_id))
    save_logos(shops)

