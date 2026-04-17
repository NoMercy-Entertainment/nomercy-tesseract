"""Shared pytest fixtures for training script tests."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def tmp_out(tmp_path: Path) -> Path:
    """Temporary output directory scoped to one test."""
    out = tmp_path / "out"
    out.mkdir()
    return out


@pytest.fixture
def sample_lines() -> list[str]:
    return [
        "The quick brown fox jumps over the lazy dog",
        "Subtitle line with special chars: \u266a \u266b",
        "Line with punctuation, dashes \u2013 and an ellipsis\u2026",
    ]
