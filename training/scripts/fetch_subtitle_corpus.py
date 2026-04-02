#!/usr/bin/env python3
"""
fetch_subtitle_corpus.py
========================
Downloads real subtitle text from the OPUS OpenSubtitles v2018 corpus,
cleans it, injects music-note variants, and writes training-ready text lines.

Usage:
    python3 fetch_subtitle_corpus.py --lang eng                            # stdout
    python3 fetch_subtitle_corpus.py --lang eng --output corpus.txt        # to file
    python3 fetch_subtitle_corpus.py --all --output-dir training/generated/
    python3 fetch_subtitle_corpus.py --all --output-dir training/generated/ --max-lines 10000

OPUS OpenSubtitles v2018 monolingual URL pattern:
    https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2018/mono/{lang}.txt.gz
"""

import argparse
import gzip
import os
import random
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

# Allow running from any working directory — build_training_text lives here
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_training_text import LANG_GROUPS, get_languages_from_tessdata


# ── Path helpers ─────────────────────────────────────────────────────────────

def repo_root() -> Path:
    """3 levels up from this script: scripts/ → training/ → nomercy-tesseract/"""
    return Path(__file__).resolve().parent.parent.parent


# ── Tesseract → OPUS ISO 639-1 language code mapping ────────────────────────
#
# OPUS uses ISO 639-1 two-letter codes. Tesseract uses ISO 639-2/T three-letter
# codes plus custom suffixes (e.g. chi_sim, jpn_vert). Where OPUS has no data
# for a code, we map to a related language or None.

TESS_TO_OPUS: Dict[str, Optional[str]] = {
    # ── Core European ────────────────────────────────────────────────────────
    "eng": "en",
    "fra": "fr",
    "deu": "de",
    "spa": "es",
    "ita": "it",
    "por": "pt",
    "nld": "nl",
    "swe": "sv",
    "nor": "no",
    "dan": "da",
    "fin": "fi",
    "pol": "pl",
    "ces": "cs",
    "slk": "sk",
    "hun": "hu",
    "ron": "ro",
    "tur": "tr",
    "hrv": "hr",
    "srp": "sr",
    "slv": "sl",
    "sqi": "sq",
    "est": "et",
    "lav": "lv",
    "lit": "lt",
    "bos": "bs",
    "mkd": "mk",
    "bel": "be",
    "cat": "ca",
    "eus": "eu",
    "glg": "gl",
    "afr": "af",
    "mlt": "mt",
    "isl": "is",
    "gle": "ga",
    "cym": "cy",
    "bre": "br",
    "fao": "fo",
    # ── Cyrillic ─────────────────────────────────────────────────────────────
    "rus": "ru",
    "ukr": "uk",
    "bul": "bg",
    "kaz": "kk",
    "mon": "mn",
    "aze_cyrl": "az",   # Azerbaijani Cyrillic — use same az data
    "uzb_cyrl": "uz",   # Uzbek Cyrillic — use same uz data
    # ── CJK ──────────────────────────────────────────────────────────────────
    "jpn": "ja",
    "kor": "ko",
    "chi_sim": "zh_cn",
    "chi_tra": "zh_tw",
    # Vertical variants use the same corpus data as horizontal
    "jpn_vert": "ja",
    "kor_vert": "ko",
    "chi_sim_vert": "zh_cn",
    "chi_tra_vert": "zh_tw",
    # ── Arabic script ─────────────────────────────────────────────────────────
    "ara": "ar",
    "fas": "fa",
    "heb": "he",
    "urd": "ur",
    # ── Indic ─────────────────────────────────────────────────────────────────
    "hin": "hi",
    "ben": "bn",
    "tam": "ta",
    "tel": "te",
    "kan": "kn",
    "mal": "ml",
    "guj": "gu",
    "pan": "pa",
    "nep": "ne",
    "mar": "mr",
    "asm": "as",
    "sin": "si",
    # ── Southeast Asian ───────────────────────────────────────────────────────
    "tha": "th",
    "vie": "vi",
    "ind": "id",
    "msa": "ms",
    "mya": "my",
    "khm": "km",
    "lao": "lo",
    "tgl": "tl",
    "fil": "tl",       # Filipino — map to Tagalog
    "ceb": None,       # Cebuano — not in OPUS
    "jav": None,       # Javanese — not in OPUS
    "sun": None,       # Sundanese — not in OPUS
    # ── Caucasian ─────────────────────────────────────────────────────────────
    "kat": "ka",
    "kat_old": "ka",   # Old Georgian — use modern Georgian data
    "hye": "hy",
    # ── African / other ───────────────────────────────────────────────────────
    "swa": "sw",
    "yor": "yo",
    "amh": "am",
    "tir": None,       # Tigrinya — not in OPUS
    # ── Germanic aliases (our custom codes) ──────────────────────────────────
    "ger": "de",       # alias for deu
    "dut": "nl",       # alias for nld
    # ── Fraktur / historical variants → use modern script data ───────────────
    "deu_frak": "de",
    "deu_latf": "de",
    "dan_frak": "da",
    "slk_frak": "sk",
    # ── Historical / archaic → fall back to modern variant ───────────────────
    "enm": "en",       # Middle English → English
    "frm": "fr",       # Middle French → French
    "spa_old": "es",   # Old Spanish → Spanish
    "ita_old": "it",   # Old Italian → Italian
    # ── Turkic ────────────────────────────────────────────────────────────────
    "aze": "az",
    "uzb": "uz",
    "kir": "ky",
    "tgk": "tg",
    "kmr": "ku",       # Kurmanji Kurdish
    "tat": "tt",
    "uig": None,       # Uyghur — not in OPUS
    # ── Other scripts ─────────────────────────────────────────────────────────
    "ell": "el",       # Greek
    "grc": None,       # Ancient Greek — not in OPUS
    "lat": None,       # Latin — not in OPUS
    "srp_latn": "sr",  # Serbian Latin — map to Serbian
    # ── Celtic / Romance ──────────────────────────────────────────────────────
    "oci": "oc",
    "cos": None,       # Corsican — not in OPUS
    "hat": "ht",       # Haitian Creole
    "epo": "eo",       # Esperanto
    "fry": "fy",       # Western Frisian
    "ltz": "lb",       # Luxembourgish
    "gla": "gd",       # Scottish Gaelic
    # ── Pacific / Amerindian / other small languages ──────────────────────────
    "mri": "mi",       # Maori
    "ton": None,       # Tongan — not in OPUS
    "que": None,       # Quechua — not in OPUS
    "chr": None,       # Cherokee — not in OPUS
    "iku": None,       # Inuktitut — not in OPUS
    "dzo": None,       # Dzongkha — not in OPUS
    # ── Scripts without OPUS data ─────────────────────────────────────────────
    "bod": None,       # Tibetan
    "ori": "or",       # Odia — try OPUS
    "san": None,       # Sanskrit
    "pus": "ps",       # Pashto
    "snd": "sd",       # Sindhi
    "div": None,       # Divehi / Maldivian
    "syr": None,       # Syriac
    "yid": "yi",       # Yiddish
    # ── Special utility models (no text) ──────────────────────────────────────
    "osd": None,
    "equ": None,
}

# OPUS base URL
_OPUS_BASE = "https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2018/mono"

# Cache directory for downloaded .gz files
_CACHE_DIR = Path("/tmp/opus_cache")

# Minimum/maximum line length for training text
_MIN_LEN = 10
_MAX_LEN = 200

# Music note characters used for injection
_NOTE_PAIRS = [
    ("\u266a", "\u266a"),   # ♪ … ♪
    ("\u266b", "\u266b"),   # ♫ … ♫
]


# ── Download ──────────────────────────────────────────────────────────────────

def _opus_url(opus_code: str) -> str:
    return f"{_OPUS_BASE}/{opus_code}.txt.gz"


def _cache_path(opus_code: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{opus_code}.txt.gz"


def stream_clean_lines(opus_code: str, max_lines: int) -> Optional[List[str]]:
    """
    Stream-download and clean lines from OPUS, capping at max_lines.
    Never loads the full file into memory — processes line by line
    through gzip streaming. English OPUS is ~4GB; this uses ~10MB.
    Returns cleaned lines on success, None on download failure.
    """
    import io
    import shutil

    cached = _cache_path(opus_code)
    url = _opus_url(opus_code)

    # Open a streaming source (cached file or HTTP)
    try:
        if cached.exists():
            raw_stream = open(cached, "rb")
        else:
            resp = urllib.request.urlopen(url, timeout=120)
            # Stream to cache file while reading (tee pattern)
            cached.parent.mkdir(parents=True, exist_ok=True)
            cache_file = open(cached, "wb")
            raw_stream = _TeeReader(resp, cache_file)
    except urllib.error.HTTPError as exc:
        print(f"  WARNING: HTTP {exc.code} fetching {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  WARNING: Network error fetching {url}: {exc.reason}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"  WARNING: IO error fetching {url}: {exc}", file=sys.stderr)
        return None

    # Stream through gzip, clean line by line, stop at max_lines
    seen: set = set()
    result: List[str] = []
    try:
        with gzip.open(raw_stream, "rt", encoding="utf-8", errors="replace") as gz:
            for raw in gz:
                if len(result) >= max_lines:
                    break
                cleaned = clean_line(raw)
                if cleaned and cleaned not in seen:
                    seen.add(cleaned)
                    result.append(cleaned)
    except Exception as exc:
        print(f"  WARNING: Error reading stream: {exc}", file=sys.stderr)
    finally:
        raw_stream.close()

    return result


class _TeeReader:
    """Wraps a readable stream, writing all data to a second file as it's read."""
    def __init__(self, source, cache_file):
        self._source = source
        self._cache = cache_file

    def read(self, size=-1):
        data = self._source.read(size)
        if data:
            self._cache.write(data)
        return data

    def readable(self):
        return True

    def close(self):
        self._source.close()
        self._cache.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ── Cleaning ──────────────────────────────────────────────────────────────────

# Patterns that identify non-subtitle content
_RE_HTML_TAG   = re.compile(r"<[^>]+>|\{[^}]+\}", re.UNICODE)
_RE_TIMESTAMP  = re.compile(r"\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3}\s*-->")
_RE_FILE_PATH  = re.compile(r"[A-Za-z]:\\|/[A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+")
_RE_ONLY_CAPS  = re.compile(r"^[^a-z\u00e0-\u024f\u0400-\u04ff]+$", re.UNICODE)


def clean_line(raw: str) -> Optional[str]:
    """
    Apply all cleaning rules to a single raw line.
    Returns the cleaned line, or None if it should be discarded.
    """
    # Strip HTML/ASS tags
    line = _RE_HTML_TAG.sub("", raw)
    # Normalize Unicode to NFC
    line = unicodedata.normalize("NFC", line)
    # Strip surrounding whitespace
    line = line.strip()

    # Discard empty
    if not line:
        return None

    # Discard length outliers
    if len(line) < _MIN_LEN or len(line) > _MAX_LEN:
        return None

    # Discard lines that are all caps with no lowercase (title cards, credits)
    if _RE_ONLY_CAPS.match(line):
        return None

    # Discard metadata markers
    if line.startswith("#"):
        return None
    if "-->" in line or _RE_TIMESTAMP.search(line):
        return None
    if "SUBTITLE" in line.upper() and len(line) < 30:
        return None
    if _RE_FILE_PATH.search(line):
        return None

    return line


def clean_corpus(raw_lines: List[str], max_lines: int) -> List[str]:
    """
    Clean raw lines, deduplicate, and cap at max_lines.
    Returns a stable list (order preserved after dedup).
    """
    seen: set = set()
    result: List[str] = []

    for raw in raw_lines:
        if len(result) >= max_lines:
            break
        cleaned = clean_line(raw)
        if cleaned is None:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)

    return result


# ── Music note injection ──────────────────────────────────────────────────────

def inject_music_notes(lines: List[str], target_ratio: float = 0.30, seed: int = 42) -> List[str]:
    """
    Inject ♪/♫ variants into the line list at approximately target_ratio.

    For every music variant needed:
      - ♪ {line} ♪     — full line bookended
      - ♫ {line} ♫     — alternate note bookended
      - ♪ {first_half} ♪ — first half of the line bookended

    Uses seed 42 for determinism. Returns a new list that mixes original
    lines with music variants.
    """
    if not lines:
        return lines

    rng = random.Random(seed)

    n_total_target = int(len(lines) / (1.0 - target_ratio))
    n_music = n_total_target - len(lines)

    if n_music <= 0:
        return lines

    # Sample source lines randomly (with replacement if needed)
    pool = lines if len(lines) >= n_music else lines * (n_music // len(lines) + 1)
    sampled = rng.sample(pool[:], min(n_music * 2, len(pool)))

    music_variants: List[str] = []
    for src in sampled:
        if len(music_variants) >= n_music:
            break
        open_note, close_note = rng.choice(_NOTE_PAIRS)
        variant_type = rng.randint(0, 2)
        if variant_type == 0:
            # Full bookend
            music_variants.append(f"{open_note} {src} {close_note}")
        elif variant_type == 1:
            # Alternate note bookend
            alt_open, alt_close = _NOTE_PAIRS[1] if open_note == _NOTE_PAIRS[0][0] else _NOTE_PAIRS[0]
            music_variants.append(f"{alt_open} {src} {alt_close}")
        else:
            # Half-line bookend
            mid = max(1, len(src) // 2)
            music_variants.append(f"{open_note} {src[:mid].rstrip()} {close_note}")

    # Interleave: shuffle everything together
    combined = lines + music_variants
    rng.shuffle(combined)
    return combined


# ── Per-language fetch pipeline ───────────────────────────────────────────────

def fetch_for_lang(
    tess_lang: str,
    max_lines: int,
    music_ratio: float = 0.30,
) -> List[str]:
    """
    Full pipeline for one Tesseract language code:
      1. Resolve OPUS code
      2. Download + decompress
      3. Clean
      4. Inject music notes
    Returns final list of training lines (may be empty if OPUS has no data).
    """
    opus_code = TESS_TO_OPUS.get(tess_lang)

    if opus_code is None:
        print(f"[{tess_lang}] No OPUS mapping — skipping download", file=sys.stderr)
        return []

    print(f"[{tess_lang}] Streaming from OPUS ({opus_code}), cap {max_lines:,} lines...")
    cleaned = stream_clean_lines(opus_code, max_lines)

    if cleaned is None:
        print(f"[{tess_lang}] Download failed — output will be empty", file=sys.stderr)
        return []

    print(f"[{tess_lang}] {len(cleaned):,} clean lines streamed")

    if not cleaned:
        print(f"[{tess_lang}] WARNING: no usable lines after cleaning", file=sys.stderr)
        return []

    final = inject_music_notes(cleaned, target_ratio=music_ratio)
    print(f"[{tess_lang}] {len(final):,} lines total (incl. music note variants)")

    return final


# ── Output helpers ────────────────────────────────────────────────────────────

def write_lines_to_file(lines: List[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_to_output_dir(tess_lang: str, lines: List[str], output_dir: Path) -> None:
    out_path = output_dir / tess_lang / f"{tess_lang}.training_text"
    write_lines_to_file(lines, out_path)
    print(f"[{tess_lang}] Written to {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    root = repo_root()
    default_out = root / "training" / "generated"

    parser = argparse.ArgumentParser(
        description=(
            "Download OPUS OpenSubtitles corpus for Tesseract training text. "
            "Outputs cleaned, music-note-augmented subtitle lines."
        )
    )

    # Language selection (mutually exclusive)
    lang_group = parser.add_mutually_exclusive_group(required=True)
    lang_group.add_argument(
        "--lang",
        metavar="TESS_LANG",
        help="Single Tesseract language code (e.g. eng, fra, deu)",
    )
    lang_group.add_argument(
        "--all",
        action="store_true",
        help="Process all languages discovered from tessdata/*.traineddata",
    )

    # Output destination
    parser.add_argument(
        "--output",
        type=Path,
        metavar="FILE",
        default=None,
        help="Output file path (single language only; default: stdout)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        metavar="DIR",
        default=default_out,
        help=(
            "Output directory for --all mode. "
            "Writes <dir>/<lang>/<lang>.training_text (default: training/generated/)"
        ),
    )

    # Tuning
    parser.add_argument(
        "--max-lines",
        type=int,
        default=10_000,
        metavar="N",
        help="Maximum clean lines per language before music injection (default: 10000)",
    )
    parser.add_argument(
        "--music-ratio",
        type=float,
        default=0.30,
        metavar="RATIO",
        help="Target fraction of output lines that are music-note variants (default: 0.30)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    root = repo_root()
    tessdata_dir = root / "tessdata"

    # Resolve target language list
    if args.all:
        langs = get_languages_from_tessdata(tessdata_dir)
        if not langs:
            print("ERROR: no .traineddata files found in tessdata/", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(langs)} language(s) in tessdata/")
        print()
    else:
        langs = [args.lang]

    # Single language — write to stdout or --output file
    if not args.all:
        lang = langs[0]
        lines = fetch_for_lang(lang, args.max_lines, args.music_ratio)

        if args.output:
            write_lines_to_file(lines, args.output)
            print(f"[{lang}] Written {len(lines):,} lines to {args.output}")
        else:
            # stdout — UTF-8 safe even on Windows
            out = sys.stdout
            if hasattr(out, "buffer"):
                import io
                out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            for line in lines:
                out.write(line + "\n")
        return

    # --all mode
    errors: List[str] = []

    for lang in langs:
        print()
        try:
            lines = fetch_for_lang(lang, args.max_lines, args.music_ratio)
            write_to_output_dir(lang, lines, args.output_dir)
        except Exception as exc:
            print(f"[{lang}] ERROR: {exc}", file=sys.stderr)
            errors.append(lang)

    print()
    print(f"Done. {len(langs) - len(errors)}/{len(langs)} language(s) succeeded.")

    if errors:
        print(f"Failed languages: {', '.join(errors)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
