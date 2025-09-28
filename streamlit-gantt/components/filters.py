"""Sidebar filter and import/export UI."""
from __future__ import annotations

from datetime import date
from typing import Dict, Iterable

import pandas as pd
import streamlit as st

from utils import state as state_utils
from utils.dates import to_timestamp
from utils.io import (
    REQUIRED_COLUMNS,
    dataframe_to_csv,
    dataframe_to_json,
    export_dataframe,
    parse_uploaded_file,
    transform_import,
)

DEFAULT_START = date(2025, 7, 1)
DEFAULT_END = date(2026, 6, 30)


def _apply_filters(
    projects_df: pd.DataFrame,
    search_text: str,
    work_types: Iterable[str],
    progress_list: Iterable[str],
    owners: Iterable[str],
) -> pd.DataFrame:
    filtered = projects_df.copy()
    if search_text:
        pattern = search_text.strip()
        mask = (
            filtered["name"].str.contains(pattern, case=False, na=False)
            | filtered["client"].str.contains(pattern, case=False, na=False)
            | filtered["site"].str.contains(pattern, case=False, na=False)
            | filtered["owner"].str.contains(pattern, case=False, na=False)
        )
        filtered = filtered[mask]
    if work_types:
        filtered = filtered[filtered["work_type"].isin(work_types)]
    if progress_list:
        filtered = filtered[filtered["progress"].isin(progress_list)]
    if owners:
        filtered = filtered[filtered["owner"].isin(owners)]
    return filtered


def _render_importer(
    projects_df: pd.DataFrame,
    segments_df: pd.DataFrame,
    filtered_projects: pd.DataFrame,
) -> None:
    st.subheader("データ入出力")
    tab_import, tab_export = st.tabs(["インポート", "エクスポート"])

    with tab_import:
        fmt = st.radio("ファイル形式", ("CSV", "JSON"), horizontal=True, key="import_format")
        upload = st.file_uploader("CSV/JSON を選択", type=[fmt.lower()], key="import_uploader")
        if upload is not None:
            try:
                df = parse_uploaded_file(upload, fmt)
            except Exception as exc:  # noqa: BLE001
                st.error(f"読み込みに失敗しました: {exc}")
                return
            st.caption("読み込んだデータを確認し、列マッピングを設定してください。")
            st.dataframe(df.head())
            mapping: Dict[str, str] = {}
            for field in REQUIRED_COLUMNS:
                options = ["未設定"] + list(df.columns)
                default_index = options.index(field) if field in df.columns else 0
                selection = st.selectbox(f"{field} 列", options=options, index=default_index)
                if selection != "未設定":
                    mapping[field] = selection
            if st.button("インポート実行", type="primary"):
                try:
                    result = transform_import(df, mapping)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"インポートに失敗しました: {exc}")
                else:
                    state_utils.replace_data(result.projects, result.segments)
                    st.success("データを読み込みました。")
    with tab_export:
        scope = st.radio("出力対象", ("現在の一覧", "全件"), horizontal=True, key="export_scope")
        fmt = st.radio("形式", ("CSV", "JSON"), horizontal=True, key="export_format")
        project_ids = None
        if scope == "現在の一覧":
            project_ids = filtered_projects["id"].tolist()
        df = export_dataframe(
            projects_df,
            segments_df,
            project_ids=project_ids,
        )
        if fmt == "CSV":
            data = dataframe_to_csv(df)
            mime = "text/csv"
            file_name = "projects.csv"
        else:
            data = dataframe_to_json(df)
            mime = "application/json"
            file_name = "projects.json"
        st.download_button("ダウンロード", data=data, file_name=file_name, mime=mime)


def render_sidebar(projects_df: pd.DataFrame, segments_df: pd.DataFrame) -> Dict[str, object]:
    """Render the sidebar and return filter state."""
    with st.sidebar:
        st.title("工事受注案件")
        date_range = st.date_input(
            "表示期間",
            value=(DEFAULT_START, DEFAULT_END),
            format="YYYY-MM-DD",
        )
        if isinstance(date_range, tuple):
            view_start, view_end = date_range
        else:
            view_start = date_range
            view_end = date_range
        st.divider()
        search_text = st.text_input("検索 (案件名/顧客/現場/担当)")
        work_types = st.multiselect(
            "工種で絞り込み",
            options=sorted(projects_df["work_type"].dropna().unique()),
        )
        progress_options = ["予定", "進行", "完了"]
        progress_list = st.multiselect("進捗で絞り込み", options=progress_options)
        owners = st.multiselect(
            "担当で絞り込み",
            options=sorted(projects_df["owner"].dropna().unique()),
        )
        filtered_projects = _apply_filters(projects_df, search_text, work_types, progress_list, owners)
        filtered_segments = segments_df[segments_df["project_id"].isin(filtered_projects["id"])]

        st.divider()
        st.subheader("表示設定")
        grid_mode = st.selectbox("グリッド", ("週", "日", "なし"))
        show_today = st.toggle("今日ラインを表示", value=True)
        zoom = st.selectbox("ズーム", ("週", "月", "四半期"), index=1)
        state_utils.update_settings({"grid_mode": grid_mode, "show_today": show_today, "zoom": zoom})

        st.divider()
        _render_importer(projects_df, segments_df, filtered_projects)

    return {
        "view_start": to_timestamp(view_start),
        "view_end": to_timestamp(view_end),
        "projects": filtered_projects,
        "segments": filtered_segments,
        "settings": state_utils.get_settings(),
        "search_text": search_text,
    }
