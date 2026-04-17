"""Tests for render_diverse — multi-variant subtitle renderer."""
from pathlib import Path

import pytest

from render_diverse import render_line_variants, VARIANTS_PER_LINE


def test_produces_expected_variant_count(tmp_out: Path):
    """Each line produces exactly VARIANTS_PER_LINE image+gt.txt pairs."""
    stems = render_line_variants(
        line="Hello world",
        seed=0,
        out_dir=tmp_out,
        stem_prefix="eng_test",
        fonts=["DejaVu Sans"],
    )
    assert len(stems) == VARIANTS_PER_LINE
    for stem in stems:
        assert (tmp_out / f"{stem}.png").exists()
        assert (tmp_out / f"{stem}.gt.txt").exists()


def test_gt_text_matches_input(tmp_out: Path):
    """Every emitted .gt.txt contains exactly the input line."""
    line = "Expected \u266a text"
    stems = render_line_variants(
        line=line,
        seed=0,
        out_dir=tmp_out,
        stem_prefix="eng_test",
        fonts=["DejaVu Sans"],
    )
    for stem in stems:
        gt = (tmp_out / f"{stem}.gt.txt").read_text(encoding="utf-8").rstrip("\n")
        assert gt == line


def test_deterministic_same_seed(tmp_out: Path):
    """Same seed produces byte-identical PNGs across calls."""
    kwargs = dict(line="Determinism check", out_dir=tmp_out,
                  stem_prefix="eng_det", fonts=["DejaVu Sans"])
    a = render_line_variants(seed=42, **kwargs)
    png_a = [(tmp_out / f"{s}.png").read_bytes() for s in a]

    for s in a:
        (tmp_out / f"{s}.png").unlink()
        (tmp_out / f"{s}.gt.txt").unlink()

    b = render_line_variants(seed=42, **kwargs)
    png_b = [(tmp_out / f"{s}.png").read_bytes() for s in b]

    assert png_a == png_b


def test_different_seed_produces_different_variants(tmp_out: Path):
    """Different seeds produce at least one different image."""
    kwargs = dict(line="Seed variance", out_dir=tmp_out,
                  stem_prefix="eng_var", fonts=["DejaVu Sans"])
    stems_a = render_line_variants(seed=1, **kwargs)
    png_a = [(tmp_out / f"{s}.png").read_bytes() for s in stems_a]

    for s in stems_a:
        (tmp_out / f"{s}.png").unlink()
        (tmp_out / f"{s}.gt.txt").unlink()

    stems_b = render_line_variants(seed=2, **kwargs)
    png_b = [(tmp_out / f"{s}.png").read_bytes() for s in stems_b]

    assert png_a != png_b, "Different seeds must produce different output"
