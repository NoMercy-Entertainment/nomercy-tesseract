"""Tests for benchmark.py — BCER computation."""
from benchmark import compute_bcer


def test_perfect_match_is_zero():
    assert compute_bcer("hello", "hello") == 0.0


def test_complete_mismatch_is_one():
    assert compute_bcer("hello", "xxxxx") == 1.0


def test_half_wrong_is_half():
    assert abs(compute_bcer("abcd", "abXY") - 0.5) < 1e-6


def test_empty_expected_empty_actual_is_zero():
    assert compute_bcer("", "") == 0.0


def test_empty_expected_nonempty_actual_is_one():
    assert compute_bcer("", "spurious") == 1.0


def test_insertion_counts():
    """Actual is longer than expected — extra chars count as errors."""
    bcer = compute_bcer("ab", "abcd")
    assert bcer > 0.0
    assert bcer <= 1.0
