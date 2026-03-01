import base64
import html
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from .config import AppConfig
from .constants import LOGO_DEFAULT_PATH, OUTPUT_DIR, SVG_TEMPLATE_PATH


def to_data_url(photo_bytes: bytes, media_type: str = "image/jpeg") -> str:
    b64 = base64.b64encode(photo_bytes).decode("ascii")
    return f"data:{media_type};base64,{b64}"


# В шаблоне SVG: главное фото (большой блок) = IMG_2587.JPG, первое доп. = IMG_2589.JPG, второе доп. = путь к png
SVG_MAIN_HREF = "IMG_2587.JPG"
SVG_MINOR1_HREF = "IMG_2589.JPG"
SVG_MINOR2_HREF = "../../ChatGPT Image 27 февр. 2026 г., 13_59_03.png"
SVG_LOGO_HREF = "C:\\Users\\user\\Downloads\\Дополнительный.png"
SVG_SPECS_GRID = """
<g id="spec-grid">
	<g>
		<path class="st15" d="M56.1,468.2c132.5-0.5,281.1-0.5,413.6,0C337.2,468.8,188.6,468.8,56.1,468.2L56.1,468.2z"/>
	</g>
	<g>
		<path class="st15" d="M56.1,534.2c132.5-0.5,281.1-0.5,413.6,0C337.2,534.7,188.6,534.7,56.1,534.2L56.1,534.2z"/>
	</g>
	<g>
		<path class="st15" d="M56.1,600.1c132.5-0.5,281.1-0.5,413.6,0C337.2,600.6,188.6,600.6,56.1,600.1L56.1,600.1z"/>
	</g>
	<g>
		<path class="st15" d="M56.1,666c132.5-0.5,281.1-0.5,413.6,0C337.2,666.6,188.6,666.6,56.1,666L56.1,666z"/>
	</g>
	<path class="st16" d="M174.2,423.3c0,8,0,16,0,24"/>
	<path class="st16" d="M174.2,489.2c0,8,0,16,0,24"/>
	<path class="st16" d="M174.2,555.1c0,8,0,16,0,24"/>
	<path class="st16" d="M174.2,621.1c0,8,0,16,0,24"/>
	<path class="st16" d="M174.2,687c0,8,0,16,0,24"/>
</g>
"""


def _esc(s: str) -> str:
    """Экранирует текст для вставки в SVG/XML."""
    return html.escape(s or "", quote=True)


def _wrap_minor_text(text: str, max_chars: int = 38, max_lines: int = 3) -> list[str]:
    """Делит описание на 3 строки, чтобы не наезжало на фото."""
    src = " ".join((text or "").replace("\r", "\n").split())
    if not src:
        return []
    words = src.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current if current else word[:max_chars])
        current = word if len(word) <= max_chars else word[max_chars:]
        if len(lines) >= max_lines - 1:
            break
    if len(lines) < max_lines and current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if len(lines) == max_lines and any(len(w) for w in words):
        used = " ".join(lines)
        if len(src) > len(used) and len(lines[-1]) > 1:
            lines[-1] = lines[-1].rstrip(". ") + "..."
    return lines


def build_svg(
    main_photo: bytes,
    minor_photo_1: bytes,
    minor_photo_2: bytes,
    logo_bytes: bytes | None,
    title_main: str,
    title_sub: str,
    text_minor: str,
    text_bottom_line1: str,
    text_bottom_line2: str,
    price: str,
    specs: list[str],
) -> str:
    """Собирает SVG из шаблона: 3 фото, логотип, все тексты (название главное/минорное, цена, до 5 характеристик)."""
    if not SVG_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Шаблон SVG не найден: {SVG_TEMPLATE_PATH}")
    template = SVG_TEMPLATE_PATH.read_text(encoding="utf-8")

    main_url = to_data_url(main_photo)
    minor1_url = to_data_url(minor_photo_1)
    minor2_url = to_data_url(minor_photo_2)
    svg = template.replace(f'xlink:href="{SVG_MAIN_HREF}"', f'xlink:href="{main_url}"')
    svg = svg.replace(f'xlink:href="{SVG_MINOR1_HREF}"', f'xlink:href="{minor1_url}"')
    svg = svg.replace(f'xlink:href="{SVG_MINOR2_HREF}"', f'xlink:href="{minor2_url}"')

    if logo_bytes is not None:
        logo_url = to_data_url(logo_bytes, "image/png")
    elif LOGO_DEFAULT_PATH.exists():
        logo_url = to_data_url(LOGO_DEFAULT_PATH.read_bytes(), "image/png")
    else:
        logo_url = None
    if logo_url:
        svg = svg.replace(f'xlink:href="{SVG_LOGO_HREF}"', f'xlink:href="{logo_url}"')

    minor_input = (text_minor or "").strip()
    if "\n" in minor_input:
        minor_lines = [line.strip() for line in minor_input.split("\n") if line.strip()]
    else:
        minor_lines = _wrap_minor_text(minor_input)
    minor_1 = _esc((minor_lines[0] if len(minor_lines) > 0 else "") or "Это решение подойдёт не только ")
    minor_2 = _esc((minor_lines[1] if len(minor_lines) > 1 else "") or "геймерам, но и дизайнерам, стримерам,  ")
    minor_3 = _esc((minor_lines[2] if len(minor_lines) > 2 else "") or "3D-моделлерам и видеомонтажёрам.")

    svg = svg.replace("Msi Bravo 15.6", _esc(title_main or "Msi Bravo 15.6"))
    svg = svg.replace("RTX 4060 Ryzen 7 7535HS", _esc(title_sub or "RTX 4060 Ryzen 7 7535HS"))
    svg = svg.replace("Это решение подойдёт не только ", minor_1)
    svg = svg.replace("геймерам, но и дизайнерам, стримерам,  ", minor_2)
    svg = svg.replace("3D-моделлерам и видеомонтажёрам.", minor_3)
    svg = svg.replace("Гарантия до 12 месяцев", _esc(text_bottom_line1 or "Гарантия до 12 месяцев"))
    svg = svg.replace("Доставка или самовывоз", _esc(text_bottom_line2 or "Доставка или самовывоз"))
    svg = svg.replace("69 990 ₽ ", _esc(price or "69 990 ₽ "))

    # Характеристики — пары «левая часть — правая часть» (до 5 пар); разделитель «—» или « - »
    has_specs = any(str(item).strip() for item in specs[:5]) if specs else False
    for i in range(5):
        left_val = ""
        right_val = ""
        if i < len(specs) and specs[i]:
            raw = str(specs[i]).strip()
            for sep in ("—", " - "):
                if sep in raw:
                    parts = raw.split(sep, 1)
                    left_val = _esc(parts[0].strip()) if parts else ""
                    right_val = _esc(parts[1].strip()) if len(parts) > 1 else ""
                    break
            else:
                left_val = _esc(raw)
        svg = svg.replace(f"PLACEHOLDER_SPEC_{i + 1}_LEFT", left_val)
        svg = svg.replace(f"PLACEHOLDER_SPEC_{i + 1}_RIGHT", right_val)

    if has_specs:
        svg = svg.replace('id="original-specs-paths"', 'id="original-specs-paths" visibility="hidden"')
        svg = svg.replace('id="user-specs" visibility="hidden"', 'id="user-specs"')
        if "id=\"spec-grid\"" not in svg:
            svg = svg.replace("</svg>", f"{SVG_SPECS_GRID}\n</svg>")

    return svg


async def render_svg_to_png(svg_content: str, output_path: Path, width: int = 1921, height: int = 1081) -> None:
    """Рендерит SVG в PNG через Playwright (viewBox шаблона 0 0 1921 1081)."""
    html_page = f"""<!doctype html><html><head><meta charset="UTF-8"/></head><body style="margin:0;background:white;">{svg_content}</body></html>"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": height})
        await page.set_content(html_page, wait_until="networkidle")
        await page.locator("svg").first.screenshot(path=str(output_path))
        await browser.close()


def build_html(config: dict[str, Any], photos: list[bytes], features: str, description: str, price: str) -> str:
    output_cfg = config["output"]
    cards_cfg = config["cards"]
    price_cfg = cards_cfg["price_block"]
    desc_cfg = cards_cfg["description_block"]

    width = int(output_cfg["width"])
    height = int(output_cfg["height"])
    padding = int(output_cfg["padding"])
    gap = int(output_cfg["gap"])
    photo_gap = int(output_cfg.get("photo_gap", gap))
    bg_color = output_cfg["background_color"]
    base_font_family = output_cfg.get("font_family", "Arial, Helvetica, sans-serif")
    grid_radius = int(output_cfg["photo_grid_border_radius"])
    left_ratio = float(output_cfg.get("left_column_ratio", 0.5))
    desc_font_family = desc_cfg.get("font_family", base_font_family)
    price_font_family = price_cfg.get("font_family", base_font_family)
    title_font_size = int(desc_cfg.get("title_font_size", desc_cfg["font_size"]))
    features_title = html.escape(desc_cfg.get("features_title", "Характеристики"))
    description_title = html.escape(desc_cfg.get("description_title", "Описание"))

    safe_features = html.escape(features).replace("\n", "<br/>")
    safe_description = html.escape(description).replace("\n", "<br/>")
    safe_price_title = html.escape(price_cfg.get("title", "Название-цена"))
    safe_price = html.escape(price)
    n = len(photos)

    def img_cell(data_url: str) -> str:
        return f'<div class="cell"><img src="{data_url}" alt="" /></div>'

    photo_urls = [to_data_url(p) for p in photos]
    if n == 1:
        u = photo_urls[0]
        photo_area = f'<div class="photo-area photo-area-1">{img_cell(u)}{img_cell(u)}{img_cell(u)}{img_cell(u)}</div>'
    elif n == 2:
        u1, u2 = photo_urls[0], photo_urls[1]
        photo_area = f'<div class="photo-area photo-area-2">{img_cell(u1)}{img_cell(u2)}{img_cell(u1)}{img_cell(u2)}</div>'
    else:
        u1, u2, u3 = photo_urls[0], photo_urls[1], photo_urls[2]
        photo_area = f'<div class="photo-strip">{img_cell(u1)}{img_cell(u2)}{img_cell(u3)}</div>'

    if n == 3:
        card_body = f"""
    <div class="three-top">{photo_area}</div>
    <div class="three-bottom">
      <div class="three-left info-block"><div class="info-title">{description_title}</div><div class="info-text">{safe_description}</div></div>
      <div class="three-right info-block"><div class="info-title">{features_title}</div><div class="info-text">{safe_features}</div></div>
    </div>
    <div class="price"><div class="price-title">{safe_price_title}</div><div class="price-value">{safe_price}</div></div>
"""
    else:
        card_body = f"""
    <div class="content">
      <div class="left">{photo_area}</div>
      <div class="right">
        <div class="info">
          <div class="info-block"><div class="info-title">{features_title}</div><div class="info-text">{safe_features}</div></div>
          <div class="info-block"><div class="info-title">{description_title}</div><div class="info-text">{safe_description}</div></div>
        </div>
      </div>
    </div>
    <div class="price"><div class="price-title">{safe_price_title}</div><div class="price-value">{safe_price}</div></div>
"""

    return f"""<!doctype html><html lang="ru"><head><meta charset="UTF-8" /><style>
*{{box-sizing:border-box;}} body{{margin:0;width:{width}px;height:{height}px;font-family:{base_font_family};background:transparent;}}
#card{{width:100%;height:100%;background:{bg_color};display:flex;flex-direction:column;padding:{padding}px;gap:{gap}px;}}
.content{{flex:1;min-height:0;display:flex;gap:{gap}px;}} .three-top{{flex:0 0 25%;min-height:0;}}
.photo-strip{{width:100%;height:100%;display:flex;gap:{photo_gap}px;}} .photo-strip .cell{{flex:1;min-width:0;min-height:0;}}
.three-bottom{{flex:1;min-height:0;display:flex;gap:{gap}px;}} .three-left,.three-right{{flex:1;min-width:0;min-height:0;}}
.left{{flex:0 0 {left_ratio * 100}%;width:{left_ratio * 100}%;min-width:0;display:flex;flex-direction:column;border-radius:{grid_radius}px;overflow:hidden;}}
.right{{flex:0 0 {(1 - left_ratio) * 100}%;width:{(1 - left_ratio) * 100}%;min-width:0;display:flex;flex-direction:column;gap:{gap}px;}}
.photo-area{{flex:1;display:flex;flex-direction:column;gap:{photo_gap}px;min-height:0;}} .photo-area-1 .cell,.photo-area-2 .cell{{flex:1;min-height:0;}}
.cell{{overflow:hidden;background:#ddd;}} .cell img{{width:100%;height:100%;object-fit:cover;object-position:center;display:block;}}
.info{{flex:1;min-height:0;display:flex;flex-direction:column;gap:{photo_gap}px;}}
.info-block{{flex:1;min-height:0;border:{desc_cfg["border"]};border-radius:{int(desc_cfg["border_radius"])}px;background:{desc_cfg["background_color"]};color:{desc_cfg["text_color"]};padding:{desc_cfg["padding"]};overflow:auto;}}
.info-title{{font-size:{title_font_size}px;font-family:{desc_font_family};font-weight:900;margin-bottom:4px;}}
.info-text{{font-size:{int(desc_cfg["font_size"])}px;font-family:{desc_font_family};line-height:{float(desc_cfg["line_height"])};font-weight:700;white-space:normal;}}
.price{{width:100%;flex-shrink:0;display:flex;align-items:center;justify-content:flex-start;gap:8px;padding:{price_cfg["padding"]};border:{price_cfg["border"]};border-radius:{int(price_cfg["border_radius"])}px;background:{price_cfg["background_color"]};color:{price_cfg["text_color"]};font-family:{price_font_family};}}
.price-title{{font-size:{max(12, int(price_cfg["font_size"]) - 20)}px;font-weight:800;line-height:1;margin-bottom:0;white-space:nowrap;}}
.price-value{{font-size:{max(12, int(price_cfg["font_size"]) - 20)}px;font-weight:900;line-height:1;white-space:nowrap;-webkit-text-stroke:{int(price_cfg["text_stroke_width"])}px {price_cfg["text_stroke_color"]};text-shadow:0 0 1px {price_cfg["text_stroke_color"]};}}
</style></head><body><div id="card">{card_body}</div></body></html>"""


async def render_png(html_content: str, width: int, height: int, output_path: Path) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": height})
        await page.set_content(html_content, wait_until="networkidle")
        await page.locator("#card").screenshot(path=str(output_path))
        await browser.close()


async def build_card_from_svg(
    main_photo: bytes,
    minor_photo_1: bytes,
    minor_photo_2: bytes,
    user_id: int,
    *,
    logo_bytes: bytes | None = None,
    title_main: str = "",
    title_sub: str = "",
    text_minor: str = "",
    text_bottom_line1: str = "",
    text_bottom_line2: str = "",
    price: str = "",
    specs: list[str] | None = None,
) -> tuple[Path, Path]:
    """Собирает карточку из шаблона SVG (3 фото, логотип, все тексты), сохраняет SVG и рендерит PNG."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    svg_path = OUTPUT_DIR / f"card_{user_id}_{ts}.svg"
    png_path = OUTPUT_DIR / f"card_{user_id}_{ts}.png"
    svg_content = build_svg(
        main_photo,
        minor_photo_1,
        minor_photo_2,
        logo_bytes,
        title_main,
        title_sub,
        text_minor,
        text_bottom_line1,
        text_bottom_line2,
        price,
        specs or [],
    )
    svg_path.write_text(svg_content, encoding="utf-8")
    await render_svg_to_png(svg_content, png_path)
    return svg_path, png_path


async def build_card(
    config: AppConfig,
    photos: list[bytes],
    features: str,
    description: str,
    price: str,
    user_id: int,
) -> tuple[Path, Path]:
    html_content = build_html(config.raw, photos, features, description, price)
    width = int(config.raw["output"]["width"])
    height = int(config.raw["output"]["height"])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"card_{user_id}_{ts}.png"
    html_output_path = OUTPUT_DIR / f"card_{user_id}_{ts}.html"
    html_export = html_content
    for idx, photo in enumerate(photos, start=1):
        html_export = html_export.replace(to_data_url(photo), f"pic{idx}.jpg")
    html_output_path.write_text(html_export, encoding="utf-8")
    await render_png(html_content, width, height, output_path)
    return output_path, html_output_path

