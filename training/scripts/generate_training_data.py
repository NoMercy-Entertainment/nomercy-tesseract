#!/usr/bin/env python3
"""
generate-training-data.py
=========================
Generates synthetic Tesseract LSTM training images that mimic DVD/Blu-ray
subtitle bitmaps. Each language gets only characters relevant to its script,
plus universal characters (music notes, punctuation).

Run ONCE (locally or via manual workflow dispatch). Output is committed to
the repo and reused by every training run.

Usage:
    python training/scripts/generate-training-data.py           # all languages
    python training/scripts/generate-training-data.py --lang eng # single
    python training/scripts/generate-training-data.py --preview  # show samples
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow is required. Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# ── Language-to-character-group mapping ──────────────────────────────────────

LANG_GROUPS: Dict[str, List[str]] = {
    # ── Western European ────────────────────────────────────────
    "eng": ["latin_western"],
    "enm": ["latin_western"],
    "spa": ["latin_western"],
    "spa_old": ["latin_western"],
    "fra": ["latin_western"],
    "frm": ["latin_western"],
    "deu": ["latin_western"],
    "deu_frak": ["latin_western"],
    "deu_latf": ["latin_western"],
    "ger": ["latin_western"],
    "ita": ["latin_western"],
    "ita_old": ["latin_western"],
    "por": ["latin_western"],
    "nld": ["latin_western"],
    "dut": ["latin_western"],
    "cat": ["latin_western"],
    "glg": ["latin_western"],
    "eus": ["latin_western"],
    "oci": ["latin_western"],
    "cos": ["latin_western"],
    "hat": ["latin_western"],
    "epo": ["latin_western"],
    "lat": ["latin_western"],
    "fry": ["latin_western"],
    "ltz": ["latin_western"],
    "bre": ["latin_western"],
    "gla": ["latin_western"],
    # ── Nordic ──────────────────────────────────────────────────
    "swe": ["latin_western", "latin_nordic"],
    "nor": ["latin_western", "latin_nordic"],
    "dan": ["latin_western", "latin_nordic"],
    "dan_frak": ["latin_western", "latin_nordic"],
    "fin": ["latin_western", "latin_nordic"],
    "isl": ["latin_western", "latin_nordic"],
    "fao": ["latin_western", "latin_nordic"],
    # ── Central/Eastern European ────────────────────────────────
    "pol": ["latin_western", "latin_polish"],
    "ces": ["latin_western", "latin_czech_slovak"],
    "slk": ["latin_western", "latin_czech_slovak"],
    "slk_frak": ["latin_western", "latin_czech_slovak"],
    "hun": ["latin_western", "latin_hungarian"],
    "ron": ["latin_western", "latin_romanian"],
    "hrv": ["latin_western", "latin_croatian_serbian_latin"],
    "srp_latn": ["latin_western", "latin_croatian_serbian_latin"],
    "slv": ["latin_western", "latin_croatian_serbian_latin"],
    "bos": ["latin_western", "latin_croatian_serbian_latin"],
    "sqi": ["latin_western", "latin_albanian"],
    "est": ["latin_western", "latin_estonian"],
    "lav": ["latin_western", "latin_latvian_lithuanian"],
    "lit": ["latin_western", "latin_latvian_lithuanian"],
    # ── Turkic ──────────────────────────────────────────────────
    "tur": ["latin_western", "latin_turkish"],
    "aze": ["latin_western", "latin_turkish"],
    "aze_cyrl": ["cyrillic"],
    "tat": ["cyrillic"],
    "uzb": ["latin_western"],
    "uzb_cyrl": ["cyrillic"],
    "kir": ["cyrillic"],
    "tgk": ["cyrillic"],
    "uig": ["arabic"],
    # ── Cyrillic ────────────────────────────────────────────────
    "rus": ["cyrillic"],
    "ukr": ["cyrillic"],
    "bul": ["cyrillic"],
    "mkd": ["cyrillic"],
    "bel": ["cyrillic"],
    "srp": ["cyrillic"],
    "kaz": ["cyrillic"],
    "mon": ["cyrillic"],
    # ── Greek ───────────────────────────────────────────────────
    "ell": ["greek"],
    "grc": ["greek"],
    # ── CJK ─────────────────────────────────────────────────────
    "jpn": ["japanese"],
    "jpn_vert": ["japanese"],
    "kor": ["korean"],
    "kor_vert": ["korean"],
    "chi_sim": ["chinese"],
    "chi_sim_vert": ["chinese"],
    "chi_tra": ["chinese"],
    "chi_tra_vert": ["chinese"],
    # ── Arabic script ───────────────────────────────────────────
    "ara": ["arabic"],
    "fas": ["arabic"],
    "urd": ["arabic"],
    "pus": ["arabic"],
    "snd": ["arabic"],
    "div": ["arabic"],
    "syr": ["arabic"],
    "kmr": ["latin_western"],
    # ── Hebrew ──────────────────────────────────────────────────
    "heb": ["hebrew"],
    "yid": ["hebrew"],
    # ── Indic ───────────────────────────────────────────────────
    "hin": ["hindi"],
    "mar": ["hindi"],
    "nep": ["hindi"],
    "san": ["hindi"],
    "ori": ["hindi"],
    "bod": ["hindi"],
    "ben": ["bengali"],
    "asm": ["bengali"],
    "tam": ["tamil"],
    "tel": ["telugu"],
    "kan": ["kannada"],
    "mal": ["malayalam"],
    "guj": ["gujarati"],
    "pan": ["punjabi"],
    # ── Southeast Asian ─────────────────────────────────────────
    "tha": ["thai"],
    "khm": ["khmer"],
    "lao": ["lao"],
    "mya": ["burmese"],
    "vie": ["latin_western", "latin_vietnamese"],
    "ind": [],
    "msa": [],
    "tgl": ["latin_tagalog"],
    "fil": ["latin_tagalog"],
    "ceb": [],
    "jav": [],
    "sun": [],
    # ── Other scripts ───────────────────────────────────────────
    "kat": ["georgian"],
    "kat_old": ["georgian"],
    "hye": ["armenian"],
    "amh": ["ethiopic"],
    "tir": ["ethiopic"],
    "sin": ["sinhala"],
    "chr": [],
    "iku": [],
    "dzo": [],
    "ton": [],
    "que": ["latin_western"],
    "mri": [],
    "yor": [],
    # ── Celtic ──────────────────────────────────────────────────
    "cym": ["latin_western", "latin_welsh"],
    "gle": ["latin_western", "latin_irish"],
    # ── African ─────────────────────────────────────────────────
    "swa": [],
    "afr": ["latin_western"],
    # ── Maltese ─────────────────────────────────────────────────
    "mlt": ["latin_western", "latin_maltese"],
    # ── Special ─────────────────────────────────────────────────
    "equ": [],
    "osd": [],
}


def get_languages_from_tessdata(tessdata_dir: Path) -> List[str]:
    """Discover all languages from .traineddata files in tessdata/."""
    return sorted(
        p.stem for p in tessdata_dir.glob("*.traineddata")
        if p.stem not in ("osd", "equ")  # skip non-language models
    )

# ── Curated subtitle fonts ──────────────────────────────────────────────────

SUBTITLE_FONT_NAMES = [
    "Arial", "arial",
    "LiberationSans", "liberation-sans",
    "DejaVuSans", "dejavu-sans",
    "NotoSans-Regular", "NotoSans",
    "FreeSans",
    "NotoSansCJK", "NotoSansCJKsc", "NotoSansCJKjp", "NotoSansCJKkr", "NotoSansCJKtc",
    "DroidSansFallback",
    "NotoSansArabic", "NotoSansHebrew", "NotoSansThai", "NotoSansDevanagari",
    "NotoSansBengali", "NotoSansKorean",
]

FONT_SEARCH_DIRS = [
    "/usr/share/fonts",
    "/System/Library/Fonts",
    "/Library/Fonts",
    "C:\\Windows\\Fonts",
]

COLOUR_SCHEMES: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = [
    ((255, 255, 255), (0, 0, 0)),
    ((255, 255, 0), (0, 0, 0)),
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


def parse_characters(path: Path) -> Dict[str, List[str]]:
    """Parse grouped characters.txt into {group_name: [characters]}."""
    groups: Dict[str, List[str]] = {}
    current_group = "universal"
    groups[current_group] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current_group = stripped[1:-1]
            groups.setdefault(current_group, [])
            continue
        for token in stripped.split():
            groups[current_group].append(token)

    return groups


def get_chars_for_lang(lang: str, groups: Dict[str, List[str]]) -> List[str]:
    """Get characters relevant to a specific language."""
    chars: List[str] = list(groups.get("universal", []))
    lang_groups = LANG_GROUPS.get(lang, [])
    for group_name in lang_groups:
        chars.extend(groups.get(group_name, []))
    # Deduplicate preserving order
    seen: Set[str] = set()
    unique: List[str] = []
    for c in chars:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def load_lines(path: Path) -> List[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def find_fonts() -> List[Path]:
    found: Dict[str, Path] = {}
    for search_dir in FONT_SEARCH_DIRS:
        p = Path(search_dir)
        if not p.is_dir():
            continue
        for font_file in p.rglob("*"):
            if font_file.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                continue
            stem = font_file.stem.lower().replace("-", "").replace("_", "")
            for name in SUBTITLE_FONT_NAMES:
                target = name.lower().replace("-", "").replace("_", "")
                if target in stem and name.lower() not in found:
                    found[name.lower()] = font_file
                    break
    return list(found.values())


def can_render(font: ImageFont.FreeTypeFont, text: str) -> bool:
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
    img = Image.new("RGB", (max(text_w + PADDING * 2, 32), max(text_h + PADDING * 2, 24)), color=bg)
    draw = ImageDraw.Draw(img)
    x, y = PADDING - bbox[0], PADDING - bbox[1]

    if OUTLINE_WIDTH > 0:
        for dx in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
            for dy in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
                if dx or dy:
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
                if not can_render(font, char):
                    continue

                for template in TEMPLATES:
                    text = template.format(c=char)
                    for fg, bg in COLOUR_SCHEMES:
                        img = render_image(text, font, fg, bg)
                        colour_tag = "w" if fg == (255, 255, 255) else "y"
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
    parser.add_argument("--output", type=Path, default=default_out)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    char_groups = parse_characters(config_dir / "characters.txt")
    tessdata_dir = root / "tessdata"
    languages = get_languages_from_tessdata(tessdata_dir)
    fonts = find_fonts()

    if not fonts:
        print("FATAL: no usable fonts found.", file=sys.stderr)
        sys.exit(1)

    print(f"Fonts: {len(fonts)} ({', '.join(f.stem for f in fonts)})")
    print(f"Character groups: {', '.join(char_groups.keys())}")
    print(f"Sizes: {FONT_SIZES}")
    print()

    target_langs = [args.lang] if args.lang else languages
    total = 0

    for lang in target_langs:
        chars = get_chars_for_lang(lang, char_groups)
        print(f"[{lang}] {len(chars)} characters ... ", end="", flush=True)
        n = generate(lang, args.output, fonts, chars, preview=args.preview)
        print(f"{n} images")
        total += n

    if not args.preview:
        print(f"\nTotal: {total} images -> {args.output}")


if __name__ == "__main__":
    main()
