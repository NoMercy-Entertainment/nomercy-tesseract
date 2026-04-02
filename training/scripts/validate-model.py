#!/usr/bin/env python3
"""
validate-model.py
=================
Tests a fine-tuned Tesseract model against every image in training/ground-truth/.
Exits with code 0 only if every image is read back with 100% character accuracy.

The CI workflow runs this after lstmtraining completes.  If it exits non-zero,
the tessdata/ files are NOT committed — the old models are preserved.

Usage
-----
    python training/scripts/validate-model.py \
        --tessdata tessdata/ \
        --lang eng

    # Run for all languages in config/languages.txt
    python training/scripts/validate-model.py --tessdata tessdata/

Requirements
------------
    tesseract must be on PATH
    pip install python-levenshtein   (optional, for edit-distance reporting)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_lines(path: Path) -> List[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def char_accuracy(expected: str, actual: str) -> float:
    """
    Simple character-level accuracy: 1 - (edit_distance / max_len).
    Returns a float in [0.0, 1.0].
    """
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0

    # Compute Levenshtein distance inline (no external dependency)
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
    return max(0.0, 1.0 - dist / max(m, n))


def run_tesseract(png_path: Path, tessdata_dir: Path, lang: str) -> str:
    """
    Run tesseract on *png_path* using *tessdata_dir* and *lang*.
    Returns the recognised text (stripped, without trailing newline).
    Raises RuntimeError on non-zero exit.
    """
    with tempfile.TemporaryDirectory() as tmp:
        out_base = os.path.join(tmp, "out")
        cmd = [
            "tesseract",
            str(png_path),
            out_base,
            "--tessdata-dir", str(tessdata_dir),
            "-l", lang,
            "--psm", "7",   # treat image as a single text line
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"tesseract failed (rc={result.returncode}):\n{result.stderr}"
            )
        out_txt = Path(out_base + ".txt")
        if not out_txt.exists():
            return ""
        return out_txt.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

def validate_lang(lang: str, gt_dir: Path, tessdata_dir: Path) -> Tuple[int, int, List[str]]:
    """
    Run validation for one language.
    Returns (passed, total, [failure_messages]).
    """
    pattern = f"{lang}_*.png"
    png_files = sorted(gt_dir.glob(pattern))

    if not png_files:
        print(f"  [{lang}] No ground-truth images found matching {pattern} — skipping.")
        return 0, 0, []

    passed = 0
    total = len(png_files)
    failures: List[str] = []

    for png_path in png_files:
        stem = png_path.stem
        gt_path = png_path.with_suffix(".gt.txt")

        if not gt_path.exists():
            failures.append(f"  MISSING gt.txt for {png_path.name}")
            continue

        expected = gt_path.read_text(encoding="utf-8").strip()

        try:
            actual = run_tesseract(png_path, tessdata_dir, lang)
        except RuntimeError as exc:
            failures.append(f"  ERROR  {stem}: {exc}")
            continue

        acc = char_accuracy(expected, actual)

        if acc >= 1.0:
            passed += 1
            print(f"  PASS   {stem}   expected={repr(expected)}")
        else:
            failures.append(
                f"  FAIL   {stem}   "
                f"expected={repr(expected)}   "
                f"actual={repr(actual)}   "
                f"accuracy={acc:.1%}"
            )

    return passed, total, failures


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    root = repo_root()
    config_dir = root / "training" / "config"
    gt_dir     = root / "training" / "ground-truth"

    parser = argparse.ArgumentParser(
        description="Validate fine-tuned Tesseract models against ground-truth data."
    )
    parser.add_argument(
        "--tessdata",
        type=Path,
        default=root / "tessdata",
        help="Path to the tessdata/ directory containing the fine-tuned .traineddata files",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Only validate this language (default: all languages in config/languages.txt)",
    )
    parser.add_argument(
        "--gt-dir",
        type=Path,
        default=gt_dir,
        help=f"Ground-truth directory (default: {gt_dir})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON report to this path (for CI consumption)",
    )
    args = parser.parse_args()

    if not args.tessdata.is_dir():
        print(f"ERROR: tessdata directory does not exist: {args.tessdata}", file=sys.stderr)
        sys.exit(1)

    languages = load_lines(config_dir / "languages.txt")
    target_langs = [args.lang] if args.lang else languages

    overall_passed = 0
    overall_total  = 0
    all_failures: List[str] = []

    for lang in target_langs:
        td_file = args.tessdata / f"{lang}.traineddata"
        if not td_file.exists():
            print(f"\n[{lang}] WARNING: {td_file} not found — skipping validation.")
            continue

        print(f"\n[{lang}] Validating against ground-truth images in {args.gt_dir} ...")
        p, t, fails = validate_lang(lang, args.gt_dir, args.tessdata)
        overall_passed += p
        overall_total  += t
        all_failures.extend(fails)
        print(f"  Result: {p}/{t} passed")

    print("\n" + "=" * 60)
    print(f"Overall: {overall_passed}/{overall_total} ground-truth images passed")

    status = "passed"
    if all_failures:
        status = "failed"
        print("\nFAILURES:")
        for msg in all_failures:
            print(msg)
        print(
            "\nValidation FAILED — tessdata/ will NOT be committed.\n"
            "Fix the model or add more training iterations and retry."
        )
    elif overall_total == 0:
        status = "no_data"
        print(
            "WARNING: no ground-truth images were found for the selected languages.\n"
            "Add .png / .gt.txt pairs to training/ground-truth/ to enable validation."
        )
    else:
        print("\nValidation PASSED — tessdata/ is ready to commit.")

    # Write JSON report for CI
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        failure_details = []
        for msg in all_failures:
            # Parse failure messages into structured data
            parts = msg.strip().split("   ")
            detail = {"raw": msg.strip()}
            for part in parts:
                if part.startswith("expected="):
                    detail["expected"] = part.split("=", 1)[1].strip("'\"")
                elif part.startswith("actual="):
                    detail["actual"] = part.split("=", 1)[1].strip("'\"")
                elif part.startswith("accuracy="):
                    detail["accuracy"] = part.split("=", 1)[1]
            failure_details.append(detail)

        report = {
            "lang": args.lang or "all",
            "status": status,
            "passed": overall_passed,
            "total": overall_total,
            "failures": failure_details,
        }
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport written to: {args.report}")

    sys.exit(1 if status == "failed" else 0)


if __name__ == "__main__":
    main()
