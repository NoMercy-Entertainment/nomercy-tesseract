#!/usr/bin/env python3
"""
generate-training-data.py
=========================
Generates synthetic Tesseract LSTM training images that mimic DVD and Blu-ray
subtitle bitmaps.

For each language in config/languages.txt it renders the characters from
config/characters.txt using every available font, at multiple sizes and colour
combinations.  Output is written to training/generated/<lang>/ as pairs of:
    <stem>.png
    <stem>.gt.txt

Those pairs are then converted to .lstmf files by the CI workflow using:
    tesseract <stem>.png <stem> --psm 7 lstm.train

Usage
-----
    # Generate everything (default, used by CI)
    python training/scripts/generate-training-data.py

    # Preview mode — renders to screen, does not write files
    python training/scripts/generate-training-data.py --preview

    # Only process one language
    python training/scripts/generate-training-data.py --lang eng

    # Override output directory
    python training/scripts/generate-training-data.py --output /tmp/synth

Requirements
------------
    pip install Pillow
    Fonts are resolved at runtime from --font-dir (default: training/fonts/).
    On the CI runner, apt-installed fonts are also searched automatically.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow is required.  Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Typical subtitle text samples.  Each entry is one line of subtitle text that
# will be rendered as a single training image.  The generator inserts the
# extra characters from characters.txt into these templates as well.
SUBTITLE_TEMPLATES = [
    "{char}",
    "{char} {char}",
    "Hello world {char}",
    "{char} Never gonna give you up {char}",
    "{char} La la la {char}",
    "I love you{char}",
    "Wait{char} don't go{char}",
    "She said{char} come here{char}",
    "{char} We will rock you {char}",
    "Yes{char}",
    "No{char}",
]

# (text_colour, background_colour)
COLOUR_SCHEMES: List[Tuple[Tuple[int,int,int], Tuple[int,int,int]]] = [
    ((255, 255, 255), (0, 0, 0)),    # white on black  (most common)
    ((255, 255, 0),   (0, 0, 0)),    # yellow on black (karaoke/songs)
    ((255, 255, 255), (0, 0, 128)),  # white on dark blue (some DVD players)
]

# Pixel sizes to render at (height in px; width is auto from text).
# Covers SD (DVD 720x480) and HD (Blu-ray 1920x1080) subtitle scales.
FONT_SIZES = [28, 32, 36, 42, 52, 64, 72]

# Padding around text in the final image (px, all sides)
PADDING = 8

# How many pixels of black outline to draw around text (0 = none)
OUTLINE_WIDTH = 1

# APT-installed font directories searched on Ubuntu/Debian CI runners
LINUX_FONT_DIRS = [
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/opentype/noto",
]

# Windows font directory (local dev)
WINDOWS_FONT_DIR = r"C:\Windows\Fonts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    """Return the repository root (two levels up from this script)."""
    return Path(__file__).resolve().parent.parent.parent


def load_lines(path: Path) -> List[str]:
    """Read non-empty, non-comment lines from a config file."""
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def collect_fonts(extra_dir: Path) -> List[Path]:
    """
    Return a list of .ttf / .otf font paths to use for rendering.
    Searches extra_dir first, then platform font directories.
    """
    candidates: List[Path] = []

    search_dirs = [extra_dir]
    if sys.platform.startswith("linux"):
        search_dirs += [Path(d) for d in LINUX_FONT_DIRS]
    elif sys.platform == "win32":
        search_dirs.append(Path(WINDOWS_FONT_DIR))

    for d in search_dirs:
        if d.is_dir():
            for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
                candidates.extend(d.glob(ext))

    if not candidates:
        print(
            "WARNING: no font files found — falling back to Pillow's built-in bitmap "
            "font.  Music notes and accented characters will NOT render correctly.\n"
            "Install fonts-dejavu or fonts-liberation on Linux, or place .ttf files "
            "in training/fonts/.",
            file=sys.stderr,
        )

    # Deduplicate by name (prefer first occurrence = extra_dir first)
    seen: set = set()
    unique: List[Path] = []
    for p in candidates:
        key = p.name.lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique


def render_image(
    text: str,
    font: ImageFont.FreeTypeFont,
    text_colour: Tuple[int,int,int],
    bg_colour: Tuple[int,int,int],
    outline_width: int = OUTLINE_WIDTH,
    padding: int = PADDING,
) -> Image.Image:
    """
    Render *text* onto a black background image that mimics a subtitle bitmap.
    Returns an RGB PIL Image.
    """
    # Measure bounding box
    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
    except AttributeError:
        # Pillow < 8.0 fallback
        w_t, h_t = draw.textsize(text, font=font)
        bbox = (0, 0, w_t, h_t)

    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    img_w = max(text_w + padding * 2, 32)
    img_h = max(text_h + padding * 2, 24)

    img = Image.new("RGB", (img_w, img_h), color=bg_colour)
    draw = ImageDraw.Draw(img)

    x = padding - bbox[0]
    y = padding - bbox[1]

    # Draw outline by rendering text offset in all 8 directions
    if outline_width > 0:
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, font=font, fill=bg_colour)

    draw.text((x, y), text, font=font, fill=text_colour)
    return img


def build_sample_texts(characters: List[str], templates: List[str]) -> List[str]:
    """
    Expand SUBTITLE_TEMPLATES with each character from characters.txt.
    Also adds single-character samples and multi-char combination samples.
    """
    samples: List[str] = []
    seen: set = set()

    def add(s: str) -> None:
        if s and s not in seen:
            seen.add(s)
            samples.append(s)

    for char in characters:
        for tmpl in templates:
            add(tmpl.format(char=char))
        # Bare character
        add(char)
        # Pairs
        add(f"{char} {char}")

    return samples


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

def generate(
    lang: str,
    output_dir: Path,
    font_paths: List[Path],
    characters: List[str],
    preview: bool = False,
) -> int:
    """
    Generate training images for one language.  Returns the number of images written.
    """
    lang_out = output_dir / lang
    if not preview:
        lang_out.mkdir(parents=True, exist_ok=True)

    sample_texts = build_sample_texts(characters, SUBTITLE_TEMPLATES)
    count = 0

    for font_path in font_paths:
        for size in FONT_SIZES:
            try:
                font = ImageFont.truetype(str(font_path), size)
            except Exception as exc:
                print(f"  skip font {font_path.name} @ {size}px: {exc}", file=sys.stderr)
                continue

            font_tag = re.sub(r"[^a-zA-Z0-9]", "_", font_path.stem.lower())

            for text in sample_texts:
                for fg, bg in COLOUR_SCHEMES:
                    img = render_image(text, font, fg, bg)

                    colour_tag = "white" if fg == (255, 255, 255) else "yellow"
                    # Build a filesystem-safe stem
                    char_tag = re.sub(r"[^a-zA-Z0-9_]", lambda m: f"u{ord(m.group()):04x}", text)
                    char_tag = char_tag[:60]  # cap length

                    stem = f"{lang}_{font_tag}_{size}px_{colour_tag}_{count:06d}"
                    count += 1

                    if preview:
                        img.show()
                        # Only show a few in preview mode
                        if count >= 5:
                            return count
                        continue

                    png_path = lang_out / f"{stem}.png"
                    gt_path  = lang_out / f"{stem}.gt.txt"

                    img.save(str(png_path))
                    gt_path.write_text(text, encoding="utf-8")

    return count


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    root = repo_root()
    config_dir   = root / "training" / "config"
    fonts_dir    = root / "training" / "fonts"
    default_out  = root / "training" / "generated"

    parser = argparse.ArgumentParser(
        description="Generate synthetic Tesseract subtitle training data."
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Only generate for this language code (default: all in config/languages.txt)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_out,
        help=f"Output directory (default: {default_out})",
    )
    parser.add_argument(
        "--font-dir",
        type=Path,
        default=fonts_dir,
        help=f"Directory containing extra .ttf/.otf fonts (default: {fonts_dir})",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show a few sample images on screen instead of writing files",
    )
    args = parser.parse_args()

    characters = load_lines(config_dir / "characters.txt")
    languages  = load_lines(config_dir / "languages.txt")
    font_paths = collect_fonts(args.font_dir)

    if not font_paths:
        print(
            "FATAL: no usable fonts.  On the CI runner this means the apt install "
            "step did not run.  Locally, install fonts-dejavu or place .ttf files "
            "in training/fonts/.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Fonts found     : {len(font_paths)}")
    print(f"Characters      : {len(characters)}")
    print(f"Font sizes      : {FONT_SIZES}")
    print(f"Colour schemes  : {len(COLOUR_SCHEMES)}")
    print()

    target_langs = [args.lang] if args.lang else languages

    for lang in target_langs:
        print(f"Generating [{lang}] ...", end=" ", flush=True)
        n = generate(lang, args.output, font_paths, characters, preview=args.preview)
        print(f"{n} images")

    if not args.preview:
        print(f"\nOutput written to: {args.output}")


if __name__ == "__main__":
    main()
