#!/usr/bin/env python3
"""HD 06f source + reference-style layout (title, 9+6, cream strips, grey bg)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "06f.jpg"
OUT = ROOT.parent / "七律长征书法-横版A4打印.jpg"
ART = Path("/opt/cursor/artifacts/七律长征书法-横版A4打印.jpg")

PAGE_W, PAGE_H = 3508, 2480
BG = (223, 221, 216)
PAPER = (252, 248, 240)
MARGIN_X = 96
ROW1_N = 9
COLS_TOTAL = 15
COL_GAP = 20
ROW_GAP = 34
PAD_X, PAD_Y = 12, 16


def trim_ink(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("L"))
    ys = np.where((arr < 200).any(axis=1))[0]
    xs = np.where((arr < 200).any(axis=0))[0]
    if len(ys) == 0 or len(xs) == 0:
        return img
    return img.crop((xs[0], ys[0], xs[-1] + 1, ys[-1] + 1))


def merge_ink_segments(path: Path, gap: int = 45, min_w: int = 35) -> list[tuple[int, int]]:
    arr = np.array(Image.open(path).convert("L"))
    h, w = arr.shape
    ink = (arr < 200).astype(np.uint8)
    col_sum = ink.sum(axis=0)
    raw: list[list[int]] = []
    in_seg = False
    for x in range(w):
        busy = col_sum[x] > h * 0.12
        if busy and not in_seg:
            s = x
            in_seg = True
        elif not busy and in_seg:
            raw.append([s, x])
            in_seg = False
    if in_seg:
        raw.append([s, w])
    merged = [raw[0]]
    for a, b in raw[1:]:
        if a - merged[-1][1] < gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [tuple(x) for x in merged if x[1] - x[0] >= min_w]


def split_at_valley(src: Image.Image, a: int, b: int) -> tuple[tuple[int, int], tuple[int, int]]:
    arr = np.array(src.crop((a, 0, b, src.height)).convert("L"))
    h = arr.shape[0]
    ink = (arr < 200).sum(axis=0)
    if len(ink) < 20:
        mid = (a + b) // 2
        return (a, mid), (mid, b)
    k = np.ones(9) / 9
    smooth = np.convolve(ink.astype(float), k, mode="same")
    inner = slice(15, len(smooth) - 15)
    sub = smooth[inner]
    i = int(np.argmin(sub)) + 15
    cut = a + i
    if cut - a < 25 or b - cut < 25:
        mid = (a + b) // 2
        return (a, mid), (mid, b)
    return (a, cut), (cut, b)


def to_n_columns(src: Image.Image, segs: list[tuple[int, int]], n: int) -> list[Image.Image]:
    segs = segs.copy()
    max_strip = 175

    def widest_i() -> int:
        return max(range(len(segs)), key=lambda i: segs[i][1] - segs[i][0])

    while len(segs) < n:
        idx = widest_i()
        a, b = segs[idx]
        if b - a < 50:
            break
        left, right = split_at_valley(src, a, b)
        segs[idx : idx + 1] = [left, right]

    while len(segs) > n:
        # merge the pair with the smallest gap between them
        idx = min(range(len(segs) - 1), key=lambda i: segs[i + 1][0] - segs[i][1])
        segs[idx] = (segs[idx][0], segs[idx + 1][1])
        segs.pop(idx + 1)

    # keep strips readable: split very wide columns even if already at n
    i = 0
    while i < len(segs):
        a, b = segs[i]
        if b - a > max_strip and len(segs) < n + 2:
            left, right = split_at_valley(src, a, b)
            segs[i : i + 1] = [left, right]
            continue
        i += 1

    cols: list[Image.Image] = []
    for a, b in segs[:n]:
        cols.append(trim_ink(src.crop((a, 0, b, src.height))))
    if len(cols) < n:
        cols.extend([cols[-1]] * (n - len(cols)))
    cols.reverse()
    return cols[:n]


def on_paper(strip: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (strip.width + 2 * PAD_X, strip.height + 2 * PAD_Y), PAPER)
    canvas.paste(strip, (PAD_X, PAD_Y))
    return canvas


def build_row(parts: list[Image.Image], max_w: int, max_h: int) -> Image.Image:
    strips = [on_paper(p) for p in parts]
    target_h = max_h
    scaled = []
    max_strip_w = int(max_w * 0.22)
    for s in strips:
        sc = min(target_h / s.height, 2.2)
        nw, nh = max(1, int(s.width * sc)), max(1, int(s.height * sc))
        if nw > max_strip_w:
            sc *= max_strip_w / nw
            nw, nh = max(1, int(s.width * sc)), max(1, int(s.height * sc))
        scaled.append(s.resize((nw, nh), Image.Resampling.LANCZOS))
    total_w = sum(s.width for s in scaled) + COL_GAP * (len(scaled) - 1)
    if total_w > max_w:
        shrink = max_w / total_w
        scaled = [
            s.resize((max(1, int(s.width * shrink)), max(1, int(s.height * shrink))), Image.Resampling.LANCZOS)
            for s in scaled
        ]
        total_w = sum(s.width for s in scaled) + COL_GAP * (len(scaled) - 1)
    row_h = max(s.height for s in scaled)
    row = Image.new("RGB", (max_w, row_h), BG)
    x = (max_w - total_w) // 2
    for s in scaled:
        row.paste(s, (x, (row_h - s.height) // 2))
        x += s.width + COL_GAP
    return row


def draw_header(draw: ImageDraw.ImageDraw) -> None:
    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/noto/NotoSerifCJK-Bold.ttc", 78
        )
        sub_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 34
        )
    except OSError:
        title_font = sub_font = ImageFont.load_default()
    draw.text((PAGE_W // 2, 56), "七律 · 长征", fill=(28, 28, 28), font=title_font, anchor="mt")
    draw.text(
        (PAGE_W // 2, 138),
        "毛泽东手书  一九六二年四月二十日",
        fill=(105, 105, 105),
        font=sub_font,
        anchor="mt",
    )


def main() -> None:
    src = Image.open(SRC).convert("RGB")
    segs = merge_ink_segments(SRC)
    cols = to_n_columns(src, segs, COLS_TOTAL)
    row1, row2 = cols[:ROW1_N], cols[ROW1_N:]

    header_h = 208
    max_w = PAGE_W - 2 * MARGIN_X
    avail = PAGE_H - header_h - ROW_GAP - 32
    row_h = avail // 2

    r1 = build_row(row1, max_w, row_h)
    r2 = build_row(row2, max_w, row_h)
    body_h = r1.height + ROW_GAP + r2.height
    body = Image.new("RGB", (max_w, body_h), BG)
    body.paste(r1, (0, 0))
    body.paste(r2, (0, r1.height + ROW_GAP))

    page = Image.new("RGB", (PAGE_W, PAGE_H), BG)
    draw = ImageDraw.Draw(page)
    draw_header(draw)
    y = header_h + max(16, (PAGE_H - header_h - body_h) // 2) - 12
    page.paste(body, (MARGIN_X, y))

    for p in (OUT, ART):
        p.parent.mkdir(parents=True, exist_ok=True)
        page.save(p, "JPEG", quality=97, dpi=(300, 300), subsampling=0, optimize=True)
    print("saved", OUT, "segments", len(segs), "layout", f"{ROW1_N}+{len(row2)}", "source", SRC.name)


if __name__ == "__main__":
    main()
