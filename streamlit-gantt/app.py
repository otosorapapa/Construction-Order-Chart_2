"""Streamlit entry point for the construction order Gantt chart app."""
from __future__ import annotations

from typing import List, Optional

import pandas as pd
import streamlit as st

try:
    import plotly.io as pio
except ModuleNotFoundError:  # pragma: no cover - run-time safeguard
    st.error(
        "Plotly が見つかりませんでした。アプリを実行する前に "
        "`pip install -r streamlit-gantt/requirements.txt` を実行してください。"
    )
    st.stop()

try:
    from streamlit_plotly_events import plotly_events
except ModuleNotFoundError:  # pragma: no cover - run-time safeguard
    st.error(
        "streamlit-plotly-events が見つかりませんでした。アプリを実行する前に "
        "`pip install -r streamlit-gantt/requirements.txt` を実行してください。"
    )
    st.stop()

from components import editor, filters, gantt
from utils import state as state_utils

DATA_PATH = "data/sample_projects.csv"

st.set_page_config(
    page_title="工事受注案件の予定表",
    layout="wide",
    page_icon="📊",
)


def _build_selection_table(projects_df: pd.DataFrame, selected_ids: List[str]) -> List[str]:
    table_df = projects_df[
        ["id", "name", "client", "site", "work_type", "owner", "progress"]
    ].copy()
    table_df["選択"] = table_df["id"].isin(selected_ids)
    table_df.set_index("id", inplace=True)
    edited_df = st.data_editor(
        table_df,
        column_config={
            "選択": st.column_config.CheckboxColumn("選択", help="ガントで強調表示"),
            "name": st.column_config.TextColumn("案件名"),
            "client": st.column_config.TextColumn("顧客"),
            "site": st.column_config.TextColumn("現場"),
            "work_type": st.column_config.TextColumn("工種"),
            "owner": st.column_config.TextColumn("担当"),
            "progress": st.column_config.TextColumn("進捗"),
        },
        hide_index=False,
        disabled=["name", "client", "site", "work_type", "owner", "progress"],
        use_container_width=True,
        key="projects_table",
    )
    selected = edited_df[edited_df["選択"]].index.tolist()
    return selected


def _render_toolbar(filtered_projects: pd.DataFrame, view_start: pd.Timestamp, view_end: pd.Timestamp) -> None:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.metric("表示件数", f"{len(filtered_projects)} 件")
        st.caption(
            f"期間: {view_start.date().isoformat()} 〜 {view_end.date().isoformat()} / Ctrl+Z/Y で元に戻す/やり直す"
        )
    with col2:
        if st.button("元に戻す (Ctrl+Z)"):
            state_utils.undo()
    with col3:
        if st.button("やり直す (Ctrl+Y)"):
            state_utils.redo()


def _download_png_button(fig) -> None:
    if not fig.data:
        st.info("PNG 出力はデータが存在する場合に利用できます。")
        return
    try:
        png_bytes = pio.to_image(fig, format="png", width=1400, height=700)
    except Exception as exc:  # noqa: BLE001
        st.error(f"PNG 生成に失敗しました: {exc}")
        return
    st.download_button("PNG 出力", data=png_bytes, file_name="gantt.png", mime="image/png")
    st.caption("PDF はブラウザの印刷機能を利用し、A3 横・余白小を推奨します。")


def main() -> None:
    """Application entry point."""
    state_utils.ensure_state(DATA_PATH)
    projects_df = state_utils.get_projects()
    segments_df = state_utils.get_segments()

    sidebar_state = filters.render_sidebar(projects_df, segments_df)
    filtered_projects = sidebar_state["projects"]
    filtered_segments = sidebar_state["segments"]
    view_start = sidebar_state["view_start"]
    view_end = sidebar_state["view_end"]

    st.title("工事受注案件の予定表（ガントチャート）")
    st.caption("紙の予定表を Web 化し、検索・入出力・画像出力などを提供します。")

    _render_toolbar(filtered_projects, view_start, view_end)

    selected_ids = list(state_utils.get_selected_projects())
    with st.container():
        col_table, col_chart = st.columns([1.2, 2], gap="medium")
        with col_table:
            st.markdown("### 案件一覧")
            selected_ids = _build_selection_table(filtered_projects, selected_ids)
            state_utils.set_selected_projects(selected_ids)
        with col_chart:
            st.markdown("### ガントチャート")
            settings = sidebar_state["settings"]
            settings["selected_projects"] = set(selected_ids)
            fig = gantt.build_gantt_figure(
                projects_df,
                filtered_segments,
                view_start,
                view_end,
                settings,
            )
            events = plotly_events(
                fig,
                click_event=True,
                hover_event=False,
                select_event=False,
                override_height=int(fig.layout.height or 600),
                key="gantt_plot",
            )
            _download_png_button(fig)

    selected_segment_id: Optional[str] = st.session_state.get("selected_segment_id")
    if events:
        selected_segment_id = events[0]["customdata"][0]
        st.session_state["selected_segment_id"] = selected_segment_id

    editor.render(selected_segment_id)


if __name__ == "__main__":
    main()
