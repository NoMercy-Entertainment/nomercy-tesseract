#!/usr/bin/env python3
"""
generate_training_data.py
=========================
Orchestrates training data generation:
1. Fetches real subtitle text from OpenSubtitles corpus
2. Merges with hand-crafted LANG_SENTENCES
3. Injects ♪ music note lines at 30% ratio
4. Writes .training_text and .fonts files per language

Usage:
    python3 training/scripts/generate_training_data.py            # all languages
    python3 training/scripts/generate_training_data.py --lang eng # single language
    python3 training/scripts/generate_training_data.py --no-fetch # skip corpus download
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


def fetch_corpus(lang: str, max_lines: int, held_out_count: int) -> tuple[list, list]:
    """Fetch corpus. Returns (training_lines, held_out_lines)."""
    try:
        from fetch_subtitle_corpus import fetch_for_lang
        return fetch_for_lang(lang, max_lines=max_lines,
                              held_out_count=held_out_count)
    except ImportError:
        print(f"  WARNING: fetch_subtitle_corpus.py not found, skipping corpus", file=sys.stderr)
        return [], []
    except Exception as exc:
        print(f"  WARNING: corpus fetch failed for {lang}: {exc}", file=sys.stderr)
        return [], []


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
    parser.add_argument("--max-lines", type=int, default=50000,
                        help="Max corpus lines per language (default: 50000)")
    parser.add_argument("--held-out-count", type=int, default=2000,
                        help="Lines reserved for benchmark eval set (default: 2000)")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip corpus download, use only LANG_SENTENCES")
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
    print(f"Corpus fetch     : {'disabled' if args.no_fetch else f'up to {args.max_lines} lines'}")
    print()

    # Header row
    print(f"  {'Lang':<16} {'Corpus':>7} {'Total':>7}   Fonts")
    print(f"  {'-'*16} {'-'*7} {'-'*7}   {'-'*40}")

    errors: list = []

    held_out_dir = root / "training" / "held-out"
    held_out_dir.mkdir(parents=True, exist_ok=True)

    for lang in target_langs:
        try:
            chars = get_chars_for_lang(lang, char_groups)

            corpus_lines: list = []
            held_out_lines: list = []
            if not args.no_fetch:
                corpus_lines, held_out_lines = fetch_corpus(
                    lang, max_lines=args.max_lines,
                    held_out_count=args.held_out_count,
                )

            txt_path = write_training_text(lang, chars, args.output_dir,
                                           corpus_lines=corpus_lines)
            write_fonts_file(lang, args.output_dir)

            if held_out_lines:
                (held_out_dir / f"{lang}.txt").write_text(
                    "\n".join(held_out_lines) + "\n", encoding="utf-8")

            line_count = txt_path.read_text(encoding="utf-8").count("\n")
            fonts = get_fonts_for_lang(lang)
            print(f"  {lang:<16} {len(corpus_lines):>7} {line_count:>7}   "
                  f"held_out={len(held_out_lines):>5}   {', '.join(fonts)}")
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
