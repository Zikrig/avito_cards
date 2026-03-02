from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
# Каталог для данных, переживающих перезапуск (примеры — examples.json). В Docker монтируется как volume.
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
# Основной шаблон SVG карточки
SVG_TEMPLATE_PATH = Path(__file__).resolve().parent / "card_template.svg"
# Альтернативные шаблоны SVG (варианты макета)
SVG_TEMPLATE2_PATH = Path(__file__).resolve().parent / "card_template2.svg"
SVG_TEMPLATE3_PATH = Path(__file__).resolve().parent / "card_template3.svg"
SVG_TEMPLATES: dict[int, Path] = {
    1: SVG_TEMPLATE_PATH,
    2: SVG_TEMPLATE2_PATH,
    3: SVG_TEMPLATE3_PATH,
}
# Логотип по умолчанию (слот «Дополнительный» в шаблоне)
LOGO_DEFAULT_PATH = Path(__file__).resolve().parent / "logo_defoult.png"

