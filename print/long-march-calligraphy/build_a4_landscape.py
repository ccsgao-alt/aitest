#!/usr/bin/env python3
"""Build landscape A4 (300 DPI) print pages for Mao Zedong's Long March calligraphy."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT_PAGES = ROOT / "pages"
OUT_MASTERS = ROOT / "masters"
PDF_PATH = ROOT.parent / "毛泽东书法-七律长征-横版A4打印.pdf"

# A4 landscape @ 300 DPI
PAGE_W, PAGE_H = 3508, 2480
MARGIN = 120
DPI = (300, 300)


def stitch_vertical(paths: list[Path]) -> Image.Image:
    images = [Image.open(p).convert("RGB") for p in paths]
    w = max(im.width for im in images)
    total_h = sum(im.height for im in images)
    canvas = Image.new("RGB", (w, total_h), (255, 255, 255))
    y = 0
    for im in images:
        x = (w - im.width) // 2
        canvas.paste(im, (x, y))
        y += im.height
    return canvas


def fit_landscape_page(img: Image.Image) -> Image.Image:
    """Scale image to fit inside landscape A4 with margins."""
    usable_w = PAGE_W - 2 * MARGIN
    usable_h = PAGE_H - 2 * MARGIN
    scale = min(usable_w / img.width, usable_h / img.height)
    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (PAGE_W, PAGE_H), (255, 255, 255))
    x = (PAGE_W - new_w) // 2
    y = (PAGE_H - new_h) // 2
    canvas.paste(resized, (x, y))
    return canvas


def paginate_tall_image(img: Image.Image, prefix: str) -> list[Path]:
    """Split a tall stitched scroll into landscape A4 band pages (top→bottom)."""
    usable_w = PAGE_W - 2 * MARGIN
    usable_h = PAGE_H - 2 * MARGIN
    scale = usable_w / img.width
    scaled = img.resize(
        (usable_w, max(1, int(img.height * scale))), Image.Resampling.LANCZOS
    )
    paths: list[Path] = []
    y = 0
    idx = 0
    while y < scaled.height:
        band_h = min(usable_h, scaled.height - y)
        band = scaled.crop((0, y, usable_w, y + band_h))
        page = Image.new("RGB", (PAGE_W, PAGE_H), (255, 255, 255))
        page.paste(band, (MARGIN, MARGIN))
        out = OUT_PAGES / f"{prefix}_{idx:02d}.jpg"
        page.save(out, "JPEG", quality=92, dpi=DPI, optimize=True)
        paths.append(out)
        y += usable_h
        idx += 1
    return paths


def cover_page() -> Path:
    from PIL import ImageDraw, ImageFont

    page = Image.new("RGB", (PAGE_W, PAGE_H), (252, 248, 240))
    draw = ImageDraw.Draw(page)
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSerifCJK-Bold.ttc", 96)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 42)
    except OSError:
        font_title = ImageFont.load_default()
        font_body = font_title

    lines = [
        "毛泽东书法《七律·长征》",
        "横版 A4 打印版 · 300 DPI",
        "",
        "收录：1962 年草书横卷、1962 年分幅拼接、",
        "李银桥留念版长卷、早期版本扫描图",
        "",
        "图源：书法空间 9610.com、人民网党史频道（见 图源说明.md）",
        "仅供学习欣赏；商用请注意版权与馆藏规定。",
    ]
    y = 380
    draw.text((PAGE_W // 2, y), lines[0], fill=(120, 20, 20), font=font_title, anchor="mt")
    y += 140
    for line in lines[1:]:
        draw.text((PAGE_W // 2, y), line, fill=(40, 40, 40), font=font_body, anchor="mt")
        y += 72 if line else 36

    poem = (
        "红军不怕远征难，万水千山只等闲。五岭逶迤腾细浪，乌蒙磅礴走泥丸。\n"
        "金沙水拍云崖暖，大渡桥横铁索寒。更喜岷山千里雪，三军过后尽开颜。"
    )
    draw.multiline_text(
        (PAGE_W // 2, PAGE_H - 420),
        poem,
        fill=(60, 60, 60),
        font=font_body,
        anchor="mm",
        align="center",
        spacing=14,
    )
    out = OUT_PAGES / "00_cover.jpg"
    page.save(out, "JPEG", quality=90, dpi=DPI)
    return out


def main() -> None:
    OUT_PAGES.mkdir(parents=True, exist_ok=True)
    OUT_MASTERS.mkdir(parents=True, exist_ok=True)
    all_pages: list[Path] = [cover_page()]

    # 1962 horizontal banner (central archive style)
    v2_banner = Image.open(ROOT / "06f.jpg").convert("RGB")
    p = OUT_PAGES / "01_1962横卷整幅.jpg"
    fit_landscape_page(v2_banner).save(p, "JPEG", quality=92, dpi=DPI, optimize=True)
    all_pages.append(p)

    # 1962 vertical segments → stitch → paginate
    v2_parts = [ROOT / f"06{c}.jpg" for c in "abcde"]
    v2_stitch = stitch_vertical(v2_parts)
    v2_stitch.save(OUT_MASTERS / "1962_分幅拼接.jpg", "JPEG", quality=95, dpi=DPI)
    all_pages.extend(paginate_tall_image(v2_stitch, "02_1962分幅"))

    # 1962 version 3 (Li Yinqiao scroll segments)
    v3_parts = [ROOT / f"06{i}.jpg" for i in range(1, 8)]
    v3_stitch = stitch_vertical(v3_parts)
    v3_stitch.save(OUT_MASTERS / "1962_李银桥版长卷拼接.jpg", "JPEG", quality=95, dpi=DPI)
    all_pages.extend(paginate_tall_image(v3_stitch, "03_1962李银桥版"))

    # Version 1 from美术报 scan
    v1 = Image.open(ROOT / "people" / "version1_068.jpg").convert("RGB")
    p = OUT_PAGES / "04_早期版本一.jpg"
    fit_landscape_page(v1).save(p, "JPEG", quality=92, dpi=DPI, optimize=True)
    all_pages.append(p)

    # People's Daily gallery (lower resolution; full scroll reference)
    people = sorted((ROOT / "people").glob("people_*.jpg"))
    if people:
        pd_stitch = stitch_vertical(people)
        pd_stitch.save(OUT_MASTERS / "人民网手书组图拼接.jpg", "JPEG", quality=90, dpi=DPI)
        all_pages.extend(paginate_tall_image(pd_stitch, "05_人民网组图"))

    # PDF
    import img2pdf

    with open(PDF_PATH, "wb") as f:
        f.write(img2pdf.convert([str(p) for p in all_pages]))

    manifest = ROOT / "pages" / "manifest.json"
    import json

    manifest.write_text(
        json.dumps([p.name for p in all_pages], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Pages: {len(all_pages)}")
    print(f"PDF: {PDF_PATH}")


if __name__ == "__main__":
    main()
