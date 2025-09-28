"""Unit tests for date utilities."""
from __future__ import annotations

import pandas as pd
import pytest

from utils.dates import clip_to_range, make_tickvals, validate_range


def test_make_tickvals_includes_expected_days() -> None:
    ticks = make_tickvals("2025-01-01", "2025-03-31")
    assert ticks[0].day == 6
    assert ticks[1].day == 12
    assert ticks[-1].month == 3
    assert ticks[-1].day == 31
    # Ensure February end handled correctly (28 days in 2025)
    feb_ticks = [ts for ts in ticks if ts.month == 2]
    assert feb_ticks[-1].day == 28


def test_clip_to_range_handles_overlap() -> None:
    clipped = clip_to_range("2024-12-25", "2025-01-05", "2025-01-01", "2025-01-31")
    assert clipped is not None
    start, end = clipped
    assert start == pd.Timestamp("2025-01-01")
    assert end == pd.Timestamp("2025-01-05")


def test_clip_to_range_returns_none_when_outside() -> None:
    assert (
        clip_to_range("2024-01-01", "2024-01-10", "2025-01-01", "2025-01-31")
        is None
    )


def test_validate_range_raises_on_invalid() -> None:
    with pytest.raises(ValueError):
        validate_range("2025-02-10", "2025-02-01")
