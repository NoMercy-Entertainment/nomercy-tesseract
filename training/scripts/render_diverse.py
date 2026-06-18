#!/usr/bin/env python3
"""
render_diverse.py
=================
Renders a single subtitle line into many visually diverse PNG variants to
teach the OCR model how real DVD/BluRay subtitles look in the wild.

Each line becomes VARIANTS_PER_LINE image+gt.txt pairs. The variant mix
samples realistic subtitle combinations: white/yellow/cyan text, bold/
italic/outline/shadow styling, multiple sizes, slight blur/noise/JPEG
degradation to simulate bitmap subtitle extraction.

The output layout (PNG + .gt.txt with matching stem) is the exact format
tesstrain expects.
"""
from __future__ import annotations

import argparse
import io
import os
import random
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

VARIANTS_PER_LINE = 4

# Realistic subtitle combinations only. DVD/BluRay subs are overwhelmingly
# white or yellow text on black, with a thin outline. No JPEG/noise — model
# first needs to learn clean shapes before robustness to degradation.
_COLOR_COMBOS: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = [
    ((255, 255, 255), (0, 0, 0)),      # white on black (dominant)
    ((255, 255, 255), (0, 0, 0)),
    ((255, 255, 255), (0, 0, 0)),
    ((255, 255, 0),   (0, 0, 0)),      # yellow on black
]

_SIZES = [32, 36]
_STYLES = ["regular", "bold"]
_OUTLINE_WIDTHS = [0, 1]
_SHADOW_OFFSETS = [0]
_DEGRADATIONS = ["none"]


@lru_cache(maxsize=512)
def _fc_match_file(query: str) -> Optional[str]:
    """Resolve a fontconfig pattern (e.g. 'Noto Sans Arabic:bold') to a file path."""
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", query],
            capture_output=True, text=True, timeout=10,
        )
        path = result.stdout.strip()
        return path or None
    except Exception:
        return None


def _resolve_font(font_name: str, style: str, size: int) -> Optional[ImageFont.FreeTypeFont]:
    # Resolve the family NAME to a real font file via fontconfig. PIL's
    # truetype(family_name) is unreliable and silently falls back to
    # load_default() — an ASCII-only bitmap that renders every non-Latin script
    # blank. fc-match maps the name to the installed file so real glyphs render.
    style_suffix = {
        "regular": "",
        "bold": ":bold",
        "italic": ":italic",
        "bold-italic": ":bold:italic",
    }[style]
    path = _fc_match_file(f"{font_name}{style_suffix}")
    if path:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass
    print(f"  WARNING: no usable font for '{font_name}' ({style}); render will be blank",
          file=sys.stderr)
    return ImageFont.load_default()


def _apply_degradation(img: Image.Image, kind: str, rng: random.Random) -> Image.Image:
    if kind == "blur":
        return img.filter(ImageFilter.GaussianBlur(radius=0.5))
    if kind == "noise":
        px = img.load()
        w, h = img.size
        for _ in range(int(w * h * 0.02)):
            x, y = rng.randrange(w), rng.randrange(h)
            r, g, b = px[x, y][:3]
            delta = rng.randint(-20, 20)
            px[x, y] = (
                max(0, min(255, r + delta)),
                max(0, min(255, g + delta)),
                max(0, min(255, b + delta)),
            )
        return img
    if kind == "jpeg":
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=60)
        buf.seek(0)
        return Image.open(buf).convert("RGB")
    return img


def _render_one(
    line: str,
    font: ImageFont.FreeTypeFont,
    text_rgb: Tuple[int, int, int],
    bg_rgb: Tuple[int, int, int],
    outline_width: int,
    shadow_offset: int,
    degradation: str,
    rng: random.Random,
) -> Image.Image:
    dummy = Image.new("RGB", (10, 10), bg_rgb)
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), line, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    margin_x = 20 + outline_width + shadow_offset
    margin_y = 12 + outline_width + shadow_offset
    img_w = text_w + margin_x * 2
    img_h = text_h + margin_y * 2

    img = Image.new("RGB", (img_w, img_h), bg_rgb)
    draw = ImageDraw.Draw(img)

    x = margin_x - bbox[0]
    y = margin_y - bbox[1]

    if shadow_offset > 0:
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            line, fill=(0, 0, 0), font=font,
        )

    if outline_width > 0:
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), line, fill=(0, 0, 0), font=font)

    draw.text((x, y), line, fill=text_rgb, font=font)

    return _apply_degradation(img, degradation, rng)


def is_junk_line(line: str) -> bool:
    """
    True for corpus lines that are not real subtitle text — emoji, private-use,
    math-alphanumeric, decorative and miscellaneous symbol runs (e.g.
    '꧁ঔৣ☬𝓓🅰ʍ𝖆я☬ঔৣ꧂'). These have no place in an OCR model and the encoder
    would skip them anyway. Real punctuation and the wanted glyphs ♪ ♫ are kept.
    """
    if not line.strip():
        return True
    for ch in line:
        cp = ord(ch)
        if (
            cp >= 0x1F000                                  # emoji & supplemental symbols
            or 0xE000 <= cp <= 0xF8FF                       # private use area
            or 0x1D400 <= cp <= 0x1D7FF                     # math alphanumeric
            or 0xA9C0 <= cp <= 0xA9CF                       # Javanese decorative
            or (0x2600 <= cp <= 0x27BF and ch not in ("♪", "♫"))  # misc symbols/dingbats
        ):
            return True
    return False


def render_line_variants(
    line: str,
    seed: int,
    out_dir: Path,
    stem_prefix: str,
    fonts: List[str],
) -> List[str]:
    """
    Render one training line as VARIANTS_PER_LINE variants. Returns the
    list of output stems (without extension). PNG + .gt.txt written side
    by side with matching stems.
    """
    if is_junk_line(line):
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    stems: List[str] = []

    for i in range(VARIANTS_PER_LINE):
        font_name = rng.choice(fonts)
        style = rng.choice(_STYLES)
        size = rng.choice(_SIZES)
        text_rgb, bg_rgb = rng.choice(_COLOR_COMBOS)
        outline = rng.choice(_OUTLINE_WIDTHS)
        shadow = rng.choice(_SHADOW_OFFSETS)
        deg = rng.choice(_DEGRADATIONS)

        font = _resolve_font(font_name, style, size)
        if font is None:
            continue

        img = _render_one(line, font, text_rgb, bg_rgb,
                          outline, shadow, deg, rng)

        stem = f"{stem_prefix}_{i:02d}"
        img.save(out_dir / f"{stem}.png", format="PNG")
        (out_dir / f"{stem}.gt.txt").write_text(line + "\n", encoding="utf-8")
        stems.append(stem)

    return stems


def _render_worker(args: tuple) -> int:
    idx, line, start_seed, out_dir_str, lang, fonts = args
    stem_prefix = f"{lang}_{idx:06d}"
    stems = render_line_variants(
        line=line,
        seed=start_seed + idx,
        out_dir=Path(out_dir_str),
        stem_prefix=stem_prefix,
        fonts=fonts,
    )
    return len(stems)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a training_text file as diverse subtitle variants."
    )
    parser.add_argument("--training-text", type=Path, required=True)
    parser.add_argument("--fonts-file", type=Path, required=True,
                        help="Newline-delimited font names")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--lang", required=True)
    parser.add_argument("--start-seed", type=int, default=0)
    parser.add_argument("--max-lines", type=int, default=0,
                        help="0 = no cap")
    parser.add_argument("--workers", type=int, default=0,
                        help="0 = auto (cpu_count)")
    args = parser.parse_args()

    fonts = [f for f in args.fonts_file.read_text().splitlines() if f]
    if not fonts:
        fonts = ["DejaVu Sans"]

    lines = args.training_text.read_text(encoding="utf-8").splitlines()
    if args.max_lines > 0:
        lines = lines[:args.max_lines]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_dir_str = str(args.out_dir)

    workers = args.workers or cpu_count()
    print(f"Rendering {len(lines)} lines with {workers} workers "
          f"({VARIANTS_PER_LINE} variants each = ~{len(lines) * VARIANTS_PER_LINE:,} PNGs)...")

    tasks = [
        (idx, line, args.start_seed, out_dir_str, args.lang, fonts)
        for idx, line in enumerate(lines)
    ]

    total = 0
    report_every = max(1, len(tasks) // 20)
    with Pool(processes=workers) as pool:
        for i, count in enumerate(pool.imap_unordered(_render_worker, tasks, chunksize=32), 1):
            total += count
            if i % report_every == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)} lines done ({total} variants)",
                      flush=True)

    print(f"Rendered {total} variants from {len(lines)} lines")


if __name__ == "__main__":
    main()
