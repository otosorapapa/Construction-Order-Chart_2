"""Segment editor rendered on the main page when a bar is selected."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from utils.dates import validate_range
from utils import state as state_utils

PROGRESS_OPTIONS = ["予定", "進行", "完了"]


def render(segment_id: Optional[str]) -> None:
    """Render the editor for the selected segment."""
    st.subheader("セグメント編集")
    if not segment_id:
        st.info("ガントチャートのバーをクリックすると編集できます。")
        return

    if st.button("選択を解除", key="clear_selection"):
        st.session_state.pop("selected_segment_id", None)
        st.experimental_rerun()

    segments_df = state_utils.get_segments()
    projects_df = state_utils.get_projects()
    segment_row = segments_df.loc[segments_df["segment_id"] == segment_id]
    if segment_row.empty:
        st.error("選択されたセグメントが見つかりません。")
        return
    segment = segment_row.iloc[0]
    project_row = projects_df.loc[projects_df["id"] == segment["project_id"]]
    if project_row.empty:
        st.error("関連する案件が見つかりません。")
        return
    project = project_row.iloc[0]

    with st.form("segment_editor"):
        label = st.text_input("ラベル", value=segment.get("label", ""))
        start_date = st.date_input(
            "開始日",
            value=segment["start_date"].date(),
            format="YYYY-MM-DD",
        )
        end_date = st.date_input(
            "終了日",
            value=segment["end_date"].date(),
            format="YYYY-MM-DD",
        )
        progress = st.selectbox("進捗", options=PROGRESS_OPTIONS, index=PROGRESS_OPTIONS.index(project["progress"]))
        note = st.text_area("メモ", value=project.get("note", ""), height=120)
        color = st.color_picker("バーの色", value=str(project.get("color", "#f97316")))
        submitted = st.form_submit_button("保存", type="primary")

    if submitted:
        try:
            start_ts, end_ts = validate_range(start_date, end_date)
        except ValueError as exc:
            st.error(str(exc))
            return
        state_utils.push_history()
        state_utils.update_segment(
            segment_id,
            {
                "label": label,
                "start_date": pd.to_datetime(start_ts),
                "end_date": pd.to_datetime(end_ts),
            },
            push=False,
        )
        state_utils.update_project(
            project["id"],
            {
                "progress": progress,
                "note": note,
                "color": color,
            },
            push=False,
        )
        st.success("更新しました。画面左のガントチャートを確認してください。")
