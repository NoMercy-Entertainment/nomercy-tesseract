#!/usr/bin/env python3
"""
benchmark.py
============
Measures OCR accuracy of a given tessdata directory against a held-out
eval set. Renders each held-out line with render_diverse.py, runs
tesseract, computes per-line BCER, aggregates to a language-level score.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_training_text import get_fonts_for_lang
from render_diverse import render_line_variants


def compute_bcer(expected: str, actual: str) -> float:
    """
    Byte-level Character Error Rate = Levenshtein(expected, actual) / len(expected).
    Capped at 1.0. Empty expected with non-empty actual returns 1.0.
    """
    if not expected and not actual:
        return 0.0
    if not expected:
        return 1.0

    a, b = expected, actual
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[j] = min(dp[j] + 1, dp[j-1] + 1, prev[j-1] + cost)
    dist = dp[n]
    return min(1.0, dist / m)


def run_tesseract(png_path: Path, tessdata_dir: Path, lang: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out_base = Path(tmp) / "out"
        cmd = [
            "tesseract", str(png_path), str(out_base),
            "--tessdata-dir", str(tessdata_dir),
            "-l", lang, "--psm", "7",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return ""
        out_txt = out_base.with_suffix(".txt")
        if not out_txt.exists():
            return ""
        return out_txt.read_text(encoding="utf-8").strip()


def benchmark_lang(
    lang: str,
    tessdata_dir: Path,
    held_out_path: Path,
    render_dir: Path,
    max_lines: int = 0,
) -> Tuple[float, int, int]:
    """Returns (bcer, n_lines, n_variants)."""
    lines = [l for l in held_out_path.read_text(encoding="utf-8").splitlines() if l]
    if max_lines > 0:
        lines = lines[:max_lines]

    fonts = get_fonts_for_lang(lang) or ["DejaVu Sans"]

    render_dir.mkdir(parents=True, exist_ok=True)
    all_bcer: List[float] = []
    variant_count = 0

    for idx, line in enumerate(lines):
        stem_prefix = f"{lang}_bench_{idx:06d}"
        stems = render_line_variants(
            line=line, seed=100000 + idx,
            out_dir=render_dir,
            stem_prefix=stem_prefix, fonts=fonts,
        )
        for stem in stems:
            png = render_dir / f"{stem}.png"
            actual = run_tesseract(png, tessdata_dir, lang)
            all_bcer.append(compute_bcer(line, actual))
            variant_count += 1

    avg_bcer = sum(all_bcer) / len(all_bcer) if all_bcer else 1.0
    return avg_bcer, len(lines), variant_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True)
    parser.add_argument("--tessdata", type=Path, required=True)
    parser.add_argument("--held-out", type=Path, required=True,
                        help="Path to held-out {lang}.txt file")
    parser.add_argument("--render-dir", type=Path,
                        default=Path("/tmp/bench_render"))
    parser.add_argument("--model-tag", required=True,
                        help="e.g. 'baseline' or 'current'")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-lines", type=int, default=0,
                        help="0 = use full held-out set")
    args = parser.parse_args()

    if not args.held_out.exists():
        print(f"ERROR: held-out file not found: {args.held_out}", file=sys.stderr)
        sys.exit(1)

    bcer, n_lines, n_variants = benchmark_lang(
        args.lang, args.tessdata, args.held_out,
        args.render_dir, args.max_lines,
    )

    result = {
        "lang": args.lang,
        "model_tag": args.model_tag,
        "n_lines": n_lines,
        "n_variants": n_variants,
        "bcer": round(bcer, 6),
        "char_accuracy": round(1.0 - bcer, 6),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
