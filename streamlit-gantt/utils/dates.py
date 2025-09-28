"""Date utility helpers for the Streamlit Gantt application."""
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, List, Optional, Tuple

import pandas as pd

DateLike = date | datetime | str | pd.Timestamp


def to_timestamp(value: DateLike) -> pd.Timestamp:
    """Convert a value into a normalized pandas ``Timestamp`` (no time part)."""
    ts = pd.to_datetime(value)
    if isinstance(ts, pd.DatetimeIndex):
        ts = ts[0]
    return pd.Timestamp(year=ts.year, month=ts.month, day=ts.day)


def month_start(ts: DateLike) -> pd.Timestamp:
    """Return the first day of the month for the provided value."""
    ts = to_timestamp(ts)
    return pd.Timestamp(year=ts.year, month=ts.month, day=1)


def month_end(ts: DateLike) -> pd.Timestamp:
    """Return the last day of the month for the provided value."""
    first = month_start(ts)
    next_month = first + pd.offsets.MonthBegin(1)
    return next_month - pd.Timedelta(days=1)


def iter_months(start: DateLike, end: DateLike) -> Iterable[pd.Timestamp]:
    """Iterate over the first day for each month between ``start`` and ``end``."""
    current = month_start(start)
    end_ts = month_start(end)
    while current <= end_ts:
        yield current
        current += pd.offsets.MonthBegin(1)


def make_month_spans(start: DateLike, end: DateLike) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """Return (month_start, month_end) tuples covering the range inclusively."""
    spans: List[Tuple[pd.Timestamp, pd.Timestamp]] = []
    start_ts = to_timestamp(start)
    end_ts = to_timestamp(end)
    for first in iter_months(start_ts, end_ts):
        last = month_end(first)
        span_start = max(start_ts, first)
        span_end = min(end_ts, last)
        spans.append((span_start, span_end))
    return spans


def make_month_labels(start: DateLike, end: DateLike) -> List[Tuple[pd.Timestamp, str]]:
    """Return label positions for month headers."""
    labels: List[Tuple[pd.Timestamp, str]] = []
    for first in iter_months(start, end):
        last = month_end(first)
        midpoint = first + (last - first) / 2
        label = f"{first.year}年{first.month}月"
        labels.append((midpoint, label))
    return labels


def make_tickvals(start: DateLike, end: DateLike) -> List[pd.Timestamp]:
    """Generate tick values at 6/12/18/24/末 for each month within the period."""
    start_ts = to_timestamp(start)
    end_ts = to_timestamp(end)
    tickvals: List[pd.Timestamp] = []
    for first in iter_months(start_ts, end_ts):
        last = month_end(first)
        for day in (6, 12, 18, 24, last.day):
            if day > last.day:
                continue
            tick = pd.Timestamp(year=first.year, month=first.month, day=day)
            if start_ts <= tick <= end_ts:
                if tickvals and tick == tickvals[-1]:
                    continue
                tickvals.append(tick)
    return tickvals


def make_week_lines(start: DateLike, end: DateLike) -> List[pd.Timestamp]:
    """Return Monday positions between start and end (inclusive)."""
    start_ts = to_timestamp(start)
    end_ts = to_timestamp(end)
    # Monday is weekday() == 0
    offset_days = (7 - start_ts.weekday()) % 7
    first_monday = start_ts + pd.Timedelta(days=offset_days)
    mondays: List[pd.Timestamp] = []
    current = first_monday
    while current <= end_ts:
        mondays.append(current)
        current += pd.Timedelta(days=7)
    return mondays


def make_day_lines(start: DateLike, end: DateLike) -> List[pd.Timestamp]:
    """Return all day boundaries between start and end (exclusive of start)."""
    start_ts = to_timestamp(start)
    end_ts = to_timestamp(end)
    days: List[pd.Timestamp] = []
    current = start_ts + pd.Timedelta(days=1)
    while current <= end_ts:
        days.append(current)
        current += pd.Timedelta(days=1)
    return days


def validate_range(start: DateLike, end: DateLike) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Ensure ``start`` is not after ``end`` and return timestamps."""
    start_ts = to_timestamp(start)
    end_ts = to_timestamp(end)
    if end_ts < start_ts:
        raise ValueError("終了日は開始日以上である必要があります")
    return start_ts, end_ts


def clip_to_range(
    start: DateLike, end: DateLike, view_start: DateLike, view_end: DateLike
) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
    """Clip a segment to the view range. Return ``None`` if fully outside."""
    start_ts, end_ts = validate_range(start, end)
    view_start_ts = to_timestamp(view_start)
    view_end_ts = to_timestamp(view_end)
    if end_ts < view_start_ts or start_ts > view_end_ts:
        return None
    clipped_start = max(start_ts, view_start_ts)
    clipped_end = min(end_ts, view_end_ts)
    return clipped_start, clipped_end


def business_days(start: DateLike, end: DateLike) -> int:
    """Count the number of business days between two dates (inclusive)."""
    start_ts, end_ts = validate_range(start, end)
    return int(pd.bdate_range(start_ts, end_ts, freq="C").size)
