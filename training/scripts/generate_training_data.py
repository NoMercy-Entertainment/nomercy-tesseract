#!/usr/bin/env python3
"""
generate_training_data.py
=========================
Thin orchestrator that drives build_training_text.py to produce
.training_text and .fonts files for every target language.

Replaces the old Pillow-based image generation approach. No PIL dependency.

Usage:
    python3 training/scripts/generate_training_data.py            # all languages
    python3 training/scripts/generate_training_data.py --lang eng # single language

Output goes to training/generated/<lang>/<lang>.training_text
                 training/generated/<lang>/<lang>.fonts
"""

import argparse
import sys
from pathlib import Path

# Allow running from any working directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_training_text import (
    get_chars_for_lang,
    get_fonts_for_lang,
    get_languages_from_tessdata,
    parse_characters,
    repo_root,
    write_fonts_file,
    write_training_text,
)


def main() -> None:
    root = repo_root()
    config_dir = root / "training" / "config"
    default_out = root / "training" / "generated"
    tessdata_dir = root / "tessdata"

    parser = argparse.ArgumentParser(
        description="Generate tesstrain .training_text and .fonts files."
    )
    parser.add_argument("--lang", default=None,
                        help="Single language code (default: all)")
    parser.add_argument("--output-dir", type=Path, default=default_out,
                        metavar="DIR",
                        help="Output directory (default: training/generated/)")
    args = parser.parse_args()

    # Load character groups once
    char_file = config_dir / "characters.txt"
    if not char_file.exists():
        print(f"ERROR: characters.txt not found at {char_file}", file=sys.stderr)
        sys.exit(1)

    char_groups = parse_characters(char_file)

    # Determine target languages
    if args.lang:
        target_langs = [args.lang]
    else:
        target_langs = get_languages_from_tessdata(tessdata_dir)
        if not target_langs:
            print("ERROR: no .traineddata files found in tessdata/", file=sys.stderr)
            sys.exit(1)

    print(f"Output directory : {args.output_dir}")
    print(f"Languages        : {len(target_langs)}")
    print(f"Character groups : {', '.join(char_groups.keys())}")
    print()

    # Header row
    print(f"  {'Lang':<16} {'Chars':>6}   {'Lines':>6}   Fonts")
    print(f"  {'-'*16} {'-'*6}   {'-'*6}   {'-'*40}")

    errors: list = []

    for lang in target_langs:
        try:
            chars = get_chars_for_lang(lang, char_groups)
            txt_path = write_training_text(lang, chars, args.output_dir)
            write_fonts_file(lang, args.output_dir)
            line_count = txt_path.read_text(encoding="utf-8").count("\n")
            fonts = get_fonts_for_lang(lang)
            print(f"  {lang:<16} {len(chars):>6}   {line_count:>6}   {', '.join(fonts)}")
        except Exception as exc:
            print(f"  {lang:<16} ERROR: {exc}", file=sys.stderr)
            errors.append((lang, exc))

    print()

    if errors:
        print(f"FAILED ({len(errors)} language(s)):", file=sys.stderr)
        for lang, exc in errors:
            print(f"  {lang}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Done. {len(target_langs)} language(s) written to {args.output_dir}")


if __name__ == "__main__":
    main()
