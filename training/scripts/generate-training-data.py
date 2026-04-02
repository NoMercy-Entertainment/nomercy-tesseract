#!/usr/bin/env python3
"""
generate-training-data.py
=========================
Generates synthetic Tesseract LSTM training images that mimic DVD and Blu-ray
subtitle bitmaps.

This script is meant to be run ONCE (locally or via manual workflow dispatch).
The output is committed to the repo and reused by every training run.
Do NOT run this on every CI build — it's wasteful and unnecessary.

Usage:
    # Generate all languages
    python training/scripts/generate-training-data.py

    # Single language
    python training/scripts/generate-training-data.py --lang eng

    # Preview (show images, don't write)
    python training/scripts/generate-training-data.py --preview

Requirements:
    pip install Pillow
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow is required. Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# ── Curated subtitle fonts ──────────────────────────────────────────────────
# Only fonts commonly used in DVD/Blu-ray subtitle rendering.
# Searched by name across platform font directories.
SUBTITLE_FONT_NAMES = [
    # Latin/European
    "Arial", "arial",
    "LiberationSans-Regular", "liberation-sans",
    "DejaVuSans", "dejavu-sans",
    "NotoSans-Regular", "NotoSans",
    "FreeSans",
    # CJK
    "NotoSansCJK-Regular", "NotoSansCJKsc-Regular",
    "NotoSansCJKjp-Regular", "NotoSansCJKkr-Regular",
    "NotoSansCJKtc-Regular",
    "DroidSansFallback",
    # Arabic/Hebrew/Thai/Hindi
    "NotoSansArabic-Regular",
    "NotoSansHebrew-Regular",
    "NotoSansThai-Regular",
    "NotoSansDevanagari-Regular",
]

FONT_SEARCH_DIRS = [
    # Linux (apt-installed)
    "/usr/share/fonts/truetype",
    "/usr/share/fonts/opentype",
    "/usr/share/fonts",
    # macOS
    "/System/Library/Fonts",
    "/Library/Fonts",
    # Windows
    "C:\\Windows\\Fonts",
]

COLOUR_SCHEMES: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = [
    ((255, 255, 255), (0, 0, 0)),   # white on black (most common)
    ((255, 255, 0), (0, 0, 0)),     # yellow on black (songs/karaoke)
]

FONT_SIZES = [32, 48, 64]

PADDING = 8
OUTLINE_WIDTH = 1

TEMPLATES = [
    "{c}",
    "{c} {c}",
    "{c} Hello world",
    "Hello {c} world",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_lines(path: Path) -> List[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            # Split space-separated characters on a single line
            for token in stripped.split():
                lines.append(token)
    return lines


def find_fonts() -> List[Path]:
    """Find curated subtitle fonts from system directories."""
    found: dict[str, Path] = {}

    for search_dir in FONT_SEARCH_DIRS:
        p = Path(search_dir)
        if not p.is_dir():
            continue
        for font_file in p.rglob("*.[tToO][tTfF][fFtT]"):
            stem = font_file.stem.lower().replace("-", "").replace("_", "")
            for name in SUBTITLE_FONT_NAMES:
                target = name.lower().replace("-", "").replace("_", "")
                if target in stem and name.lower() not in found:
                    found[name.lower()] = font_file
                    break

    return list(found.values())


def can_render(font: ImageFont.FreeTypeFont, text: str) -> bool:
    """Check if a font can render the given text (no missing glyphs)."""
    try:
        probe = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(probe)
        bbox = draw.textbbox((0, 0), text, font=font)
        return (bbox[2] - bbox[0]) > 0 and (bbox[3] - bbox[1]) > 0
    except Exception:
        return False


def render_image(
    text: str,
    font: ImageFont.FreeTypeFont,
    fg: Tuple[int, int, int],
    bg: Tuple[int, int, int],
) -> Image.Image:
    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), text, font=font)

    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    img_w = max(text_w + PADDING * 2, 32)
    img_h = max(text_h + PADDING * 2, 24)

    img = Image.new("RGB", (img_w, img_h), color=bg)
    draw = ImageDraw.Draw(img)
    x = PADDING - bbox[0]
    y = PADDING - bbox[1]

    # Outline
    if OUTLINE_WIDTH > 0:
        for dx in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
            for dy in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, font=font, fill=bg)

    draw.text((x, y), text, font=font, fill=fg)
    return img


def generate(
    lang: str,
    output_dir: Path,
    fonts: List[Path],
    characters: List[str],
    preview: bool = False,
) -> int:
    lang_out = output_dir / lang
    if not preview:
        lang_out.mkdir(parents=True, exist_ok=True)

    count = 0

    for font_path in fonts:
        for size in FONT_SIZES:
            try:
                font = ImageFont.truetype(str(font_path), size)
            except Exception:
                continue

            font_tag = re.sub(r"[^a-zA-Z0-9]", "_", font_path.stem.lower())

            for char in characters:
                # Skip characters this font can't render
                if not can_render(font, char):
                    continue

                for template in TEMPLATES:
                    text = template.format(c=char)

                    for fg, bg in COLOUR_SCHEMES:
                        img = render_image(text, font, fg, bg)
                        colour_tag = "w" if fg[0] == 255 and fg[1] == 255 and fg[2] == 255 else "y"
                        stem = f"{lang}_{font_tag}_{size}px_{colour_tag}_{count:06d}"
                        count += 1

                        if preview:
                            img.show()
                            if count >= 5:
                                return count
                            continue

                        img.save(str(lang_out / f"{stem}.png"))
                        (lang_out / f"{stem}.gt.txt").write_text(text, encoding="utf-8")

    return count


def main() -> None:
    root = repo_root()
    config_dir = root / "training" / "config"
    default_out = root / "training" / "generated"

    parser = argparse.ArgumentParser(description="Generate synthetic subtitle training images.")
    parser.add_argument("--lang", default=None, help="Single language code (default: all)")
    parser.add_argument("--output", type=Path, default=default_out, help="Output directory")
    parser.add_argument("--preview", action="store_true", help="Show samples, don't write files")
    args = parser.parse_args()

    characters = load_lines(config_dir / "characters.txt")
    languages = load_lines(config_dir / "languages.txt")
    fonts = find_fonts()

    if not fonts:
        print("FATAL: no usable fonts found.", file=sys.stderr)
        print("Install fonts-noto-cjk, fonts-dejavu, fonts-liberation, or place .ttf in training/fonts/", file=sys.stderr)
        sys.exit(1)

    print(f"Fonts: {len(fonts)} ({', '.join(f.stem for f in fonts)})")
    print(f"Characters: {len(characters)}")
    print(f"Sizes: {FONT_SIZES}")
    print(f"Colours: {len(COLOUR_SCHEMES)}")
    print()

    target_langs = [args.lang] if args.lang else languages

    for lang in target_langs:
        print(f"[{lang}] ", end="", flush=True)
        n = generate(lang, args.output, fonts, characters, preview=args.preview)
        print(f"{n} images")

    if not args.preview:
        print(f"\nOutput: {args.output}")


if __name__ == "__main__":
    main()
