#!/usr/bin/env python3
"""One landscape A4 image: title header + two-row column layout (reference style)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "06f.jpg"
OUT = ROOT.parent / "七律长征书法-横版A4打印.jpg"
ART = Path("/opt/cursor/artifacts/七律长征书法-横版A4打印.jpg")

PAGE_W, PAGE_H = 3508, 2480
BG = (235, 233, 228)
MARGIN_X = 120
TITLE_H = 200
GAP_Y = 36


def find_column_cuts(gray: np.ndarray) -> list[int]:
    ink = (gray < 200).sum(axis=0).astype(float)
    w = 21
    kernel = np.ones(w) / w
    smooth = np.convolve(ink, kernel, mode="same")
    cuts = [0]
    i = 30
    while i < gray.shape[1] - 30:
        window = smooth[max(0, i - 25) : i + 26]
        if smooth[i] <= window.min() + 1 and smooth[i] < smooth.max() * 0.12:
            if i - cuts[-1] > 70:
                cuts.append(i)
        i += 1
    cuts.append(gray.shape[1])
    # merge cuts that are too close (false splits inside a column)
    merged = [cuts[0]]
    for c in cuts[1:]:
        if c - merged[-1] < 115:
            continue
        merged.append(c)
    if merged[-1] != gray.shape[1]:
        merged.append(gray.shape[1])
    return merged


def trim_column(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("L"))
    rows = np.where((arr < 200).any(axis=1))[0]
    cols = np.where((arr < 200).any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return img
    pad = 8
    top, bottom = max(0, rows[0] - pad), min(img.height, rows[-1] + pad)
    left, right = max(0, cols[0] - pad), min(img.width, cols[-1] + pad)
    return img.crop((left, top, right, bottom))


def extract_columns(src: Image.Image) -> list[Image.Image]:
    gray = np.array(src.convert("L"))
    cuts = find_column_cuts(gray)
    cols: list[Image.Image] = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < 40:
            continue
        col = trim_column(src.crop((a, 0, b, src.height)))
        if col.width >= 25 and col.height >= 80:
            cols.append(col)
    # scroll reads right-to-left: keep order (first col is rightmost in image = index 0 on right)
    return cols


def layout_columns(
    cols: list[Image.Image], width: int, row1_count: int
) -> tuple[Image.Image, int]:
    row1 = cols[:row1_count]
    row2 = cols[row1_count:]
    usable_h = (PAGE_H - TITLE_H - GAP_Y * 3) // 2

    def build_row(parts: list[Image.Image], max_w: int) -> Image.Image | None:
        if not parts:
            return None
        gap = 28
        heights = [min(usable_h, int(p.height * (max_w / sum(p.width + gap for p in parts)))) for p in parts]
        # scale each to same row height
        target_h = min(usable_h, max(int(p.height * 1.0) for p in parts))
        scaled = []
        for p in parts:
            s = min(target_h / p.height, 1.6)
            scaled.append(p.resize((max(1, int(p.width * s)), max(1, int(p.height * s))), Image.Resampling.LANCZOS))
        total_w = sum(im.width for im in scaled) + gap * (len(scaled) - 1)
        if total_w > max_w:
            shrink = max_w / total_w
            scaled = [
                im.resize((max(1, int(im.width * shrink)), max(1, int(im.height * shrink))), Image.Resampling.LANCZOS)
                for im in scaled
            ]
            total_w = sum(im.width for im in scaled) + gap * (len(scaled) - 1)
        row_h = max(im.height for im in scaled)
        canvas = Image.new("RGB", (max_w, row_h), BG)
        x = (max_w - total_w) // 2
        for im in scaled:
            y = (row_h - im.height) // 2
            canvas.paste(im, (x, y))
            x += im.width + gap
        return canvas

    max_w = width
    r1 = build_row(row1, max_w)
    r2 = build_row(row2, max_w)
    heights = [r.height for r in (r1, r2) if r]
    total_h = sum(heights) + (GAP_Y if r1 and r2 else 0)
    block = Image.new("RGB", (max_w, total_h), BG)
    y = 0
    for r in (r1, r2):
        if r is None:
            continue
        block.paste(r, (0, y))
        y += r.height + GAP_Y
    return block, total_h


def draw_header(draw: ImageDraw.ImageDraw) -> None:
    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/noto/NotoSerifCJK-Bold.ttc", 72
        )
        sub_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 36
        )
    except OSError:
        title_font = sub_font = ImageFont.load_default()
    draw.text((PAGE_W // 2, 52), "七律 · 长征", fill=(30, 30, 30), font=title_font, anchor="mt")
    draw.text(
        (PAGE_W // 2, 130),
        "毛泽东手书  一九六二年四月二十日",
        fill=(90, 90, 90),
        font=sub_font,
        anchor="mt",
    )


def main() -> None:
    src = Image.open(SRC).convert("RGB")
    cols = extract_columns(src)
  # 8+rest matches common album layout
    row1 = 9 if len(cols) >= 12 else max(6, (len(cols) + 1) // 2)
    body, body_h = layout_columns(cols, PAGE_W - 2 * MARGIN_X, row1)

    page = Image.new("RGB", (PAGE_W, PAGE_H), BG)
    draw = ImageDraw.Draw(page)
    draw_header(draw)

    y = TITLE_H + (PAGE_H - TITLE_H - body_h) // 2 - 20
    page.paste(body, (MARGIN_X, y))

    for p in (OUT, ART):
        p.parent.mkdir(parents=True, exist_ok=True)
        page.save(p, "JPEG", quality=96, dpi=(300, 300), optimize=True)
        print("saved", p, "columns", len(cols), "row1", row1)


if __name__ == "__main__":
    main()
