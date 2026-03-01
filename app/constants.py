from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
# Шаблон SVG карточки (рядом с кодом, чтобы находился при любом рабочем каталоге/Docker)
SVG_TEMPLATE_PATH = Path(__file__).resolve().parent / "card_template.svg"
# Логотип по умолчанию (слот «Дополнительный» в шаблоне)
LOGO_DEFAULT_PATH = Path(__file__).resolve().parent / "logo_defoult.png"

