import base64
import html
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from .config import AppConfig
from .constants import OUTPUT_DIR


def to_data_url(photo_bytes: bytes) -> str:
    b64 = base64.b64encode(photo_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


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

