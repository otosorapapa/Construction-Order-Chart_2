"""Utility package exports for the Streamlit Gantt app."""
from __future__ import annotations

from typing import Literal, TypedDict

WorkType = Literal["建築", "土木", "その他"]
ProgressState = Literal["予定", "進行", "完了"]


class Project(TypedDict, total=False):
    """Type definition for a project item."""

    id: str
    name: str
    client: str
    site: str
    work_type: WorkType
    owner: str
    progress: ProgressState
    note: str
    color: str


class Segment(TypedDict, total=False):
    """Type definition for a segment belonging to a project."""

    segment_id: str
    project_id: str
    label: str
    start_date: str
    end_date: str
