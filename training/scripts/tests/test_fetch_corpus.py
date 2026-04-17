"""Tests for held-out split in fetch_subtitle_corpus."""
from fetch_subtitle_corpus import split_held_out


def test_split_reserves_last_n_lines():
    lines = [f"line{i}" for i in range(100)]
    train, held = split_held_out(lines, held_out_count=10)
    assert len(train) == 90
    assert len(held) == 10
    assert set(train).isdisjoint(set(held))


def test_split_no_holdout():
    lines = [f"line{i}" for i in range(50)]
    train, held = split_held_out(lines, held_out_count=0)
    assert train == lines
    assert held == []


def test_split_held_out_larger_than_corpus():
    """If requested held-out > corpus size, reserve half, keep half for training."""
    lines = [f"line{i}" for i in range(10)]
    train, held = split_held_out(lines, held_out_count=50)
    assert len(train) == 5
    assert len(held) == 5
    assert set(train).isdisjoint(set(held))


def test_split_is_deterministic():
    lines = [f"line{i}" for i in range(100)]
    a_train, a_held = split_held_out(lines, held_out_count=10)
    b_train, b_held = split_held_out(lines, held_out_count=10)
    assert a_train == b_train
    assert a_held == b_held
