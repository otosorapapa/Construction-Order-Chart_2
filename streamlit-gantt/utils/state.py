"""Session state helpers including undo/redo management."""
from __future__ import annotations

from typing import Dict, Iterable

import pandas as pd
import streamlit as st

from .io import load_sample_data

MAX_HISTORY = 20


def ensure_state(sample_csv: str) -> None:
    """Initialize session state on first load."""
    if "projects_df" in st.session_state and "segments_df" in st.session_state:
        return
    projects_df, segments_df = load_sample_data(sample_csv)
    st.session_state["projects_df"] = projects_df
    st.session_state["segments_df"] = segments_df
    st.session_state["history"] = []
    st.session_state["future"] = []
    st.session_state.setdefault(
        "settings",
        {
            "grid_mode": "週",
            "show_today": True,
            "zoom": "月",
        },
    )
    st.session_state.setdefault("selected_projects", set())


def get_projects() -> pd.DataFrame:
    return st.session_state["projects_df"]


def get_segments() -> pd.DataFrame:
    return st.session_state["segments_df"]


def _snapshot() -> Dict[str, pd.DataFrame]:
    return {
        "projects": st.session_state["projects_df"].copy(deep=True),
        "segments": st.session_state["segments_df"].copy(deep=True),
    }


def push_history() -> None:
    history = st.session_state.get("history", [])
    history.append(_snapshot())
    if len(history) > MAX_HISTORY:
        history.pop(0)
    st.session_state["history"] = history
    st.session_state["future"] = []


def replace_data(projects_df: pd.DataFrame, segments_df: pd.DataFrame, push: bool = True) -> None:
    if push:
        push_history()
    st.session_state["projects_df"] = projects_df.copy(deep=True)
    st.session_state["segments_df"] = segments_df.copy(deep=True)


def update_project(project_id: str, updates: Dict[str, object], push: bool = True) -> None:
    if push:
        push_history()
    projects_df = get_projects().copy(deep=True)
    mask = projects_df["id"] == project_id
    for key, value in updates.items():
        if key not in projects_df.columns:
            continue
        projects_df.loc[mask, key] = value
    st.session_state["projects_df"] = projects_df


def update_segment(segment_id: str, updates: Dict[str, object], push: bool = True) -> None:
    if push:
        push_history()
    segments_df = get_segments().copy(deep=True)
    mask = segments_df["segment_id"] == segment_id
    for key, value in updates.items():
        if key not in segments_df.columns:
            continue
        segments_df.loc[mask, key] = value
    st.session_state["segments_df"] = segments_df


def undo() -> None:
    history = st.session_state.get("history", [])
    if not history:
        st.warning("元に戻す履歴がありません")
        return
    snapshot = history.pop()
    future = st.session_state.get("future", [])
    future.append(_snapshot())
    st.session_state["projects_df"] = snapshot["projects"]
    st.session_state["segments_df"] = snapshot["segments"]
    st.session_state["history"] = history
    st.session_state["future"] = future


def redo() -> None:
    future = st.session_state.get("future", [])
    if not future:
        st.warning("やり直しできる履歴がありません")
        return
    snapshot = future.pop()
    push_history()
    st.session_state["projects_df"] = snapshot["projects"]
    st.session_state["segments_df"] = snapshot["segments"]
    st.session_state["future"] = future


def set_selected_projects(project_ids: Iterable[str]) -> None:
    st.session_state["selected_projects"] = set(project_ids)


def get_selected_projects() -> set[str]:
    return set(st.session_state.get("selected_projects", set()))


def get_settings() -> Dict[str, object]:
    return dict(st.session_state.get("settings", {}))


def update_settings(updates: Dict[str, object]) -> None:
    settings = st.session_state.get("settings", {}).copy()
    settings.update(updates)
    st.session_state["settings"] = settings
