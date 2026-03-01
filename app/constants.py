from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
# Шаблон SVG карточки (главное фото + 2 дополнительных)
SVG_TEMPLATE_PATH = BASE_DIR / "1 2-01.svg"

