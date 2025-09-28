"""Plotly based Gantt chart builder."""
from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.dates import (
    clip_to_range,
    make_day_lines,
    make_month_labels,
    make_month_spans,
    make_tickvals,
    make_week_lines,
)

PROGRESS_COLORS = {"予定": "#fbbf24", "進行": "#f97316", "完了": "#22c55e"}
DEFAULT_BAR_COLOR = "#f97316"
GRID_COLOR = "rgba(148, 163, 184, 0.5)"


def _prepare_segments(
    projects_df: pd.DataFrame,
    segments_df: pd.DataFrame,
    view_start: pd.Timestamp,
    view_end: pd.Timestamp,
    selected_projects: Iterable[str],
) -> pd.DataFrame:
    project_lookup = projects_df.set_index("id")
    rows: List[Dict[str, object]] = []
    offset_tracker: Dict[str, int] = {}
    for _, segment in segments_df.iterrows():
        project_id = segment.get("project_id")
        if project_id not in project_lookup.index:
            continue
        project = project_lookup.loc[project_id]
        clipped = clip_to_range(segment["start_date"], segment["end_date"], view_start, view_end)
        if clipped is None:
            continue
        start, end = clipped
        offset = offset_tracker.get(project_id, 0)
        offset_tracker[project_id] = offset + 1
        display_name = project["name"] + ("\u2003" * offset)
        rows.append(
            {
                "segment_id": segment["segment_id"],
                "project_id": project_id,
                "project_name": project["name"],
                "label": segment.get("label", ""),
                "start": start,
                "end": end,
                "progress": project.get("progress", "予定"),
                "color": project.get("color") or DEFAULT_BAR_COLOR,
                "display": display_name,
                "is_selected": project_id in set(selected_projects),
            }
        )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df.sort_values(by=["project_name", "start"], inplace=True)
    return df


def build_gantt_figure(
    projects_df: pd.DataFrame,
    segments_df: pd.DataFrame,
    view_start: pd.Timestamp,
    view_end: pd.Timestamp,
    settings: Dict[str, object],
) -> go.Figure:
    """Build a Plotly figure representing the current gantt chart."""
    selected_projects = settings.get("selected_projects", set())
    data = _prepare_segments(projects_df, segments_df, view_start, view_end, selected_projects)
    if data.empty:
        fig = go.Figure()
        fig.update_layout(
            height=400,
            xaxis=dict(range=[view_start, view_end]),
            yaxis=dict(showticklabels=False),
            annotations=[
                dict(
                    text="表示できる工期がありません",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                )
            ],
        )
        return fig

    custom_data = ["segment_id", "project_id", "label", "project_name", "is_selected"]
    fig = px.timeline(
        data,
        x_start="start",
        x_end="end",
        y="display",
        color="progress",
        color_discrete_map=PROGRESS_COLORS,
        custom_data=custom_data,
        hover_data={"label": True, "project_name": False},
        text="label",
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[3]}</b><br>ラベル: %{customdata[2]}<br>開始: %{x|%Y-%m-%d}<br>終了: %{x_end|%Y-%m-%d}<extra></extra>",
        textposition="inside",
        insidetextanchor="middle",
    )

    zoom = settings.get("zoom", "月")
    tickvals = make_tickvals(view_start, view_end)
    if zoom == "週":
        tickvals = sorted(set(tickvals + make_week_lines(view_start, view_end)))
    elif zoom == "四半期":
        quarter_starts = []
        for span_start, _ in make_month_spans(view_start, view_end):
            if span_start.month in (1, 4, 7, 10):
                quarter_starts.append(span_start)
        if quarter_starts:
            tickvals = sorted(set(tickvals + quarter_starts))
    tick_format = "%d" if zoom == "月" else "%m/%d"
    fig.update_xaxes(
        type="date",
        tickvals=tickvals,
        tickformat=tick_format,
        tickfont=dict(size=12),
        range=[view_start, view_end + pd.Timedelta(days=1)],
        showgrid=False,
    )
    fig.update_yaxes(autorange="reversed", title=None)

    for trace in fig.data:
        widths = []
        line_colors = []
        marker_colors = []
        colors = trace.marker.color
        if not isinstance(colors, (list, tuple)):
            colors = [colors] * len(trace.customdata)
        for cd, base_color in zip(trace.customdata, colors):
            selected = cd[4]
            widths.append(3 if selected else 1)
            line_colors.append("#1f2937" if selected else "rgba(55, 65, 81, 0.4)")
            marker_colors.append(base_color)
        trace.update(marker=dict(line=dict(width=widths, color=line_colors), color=marker_colors))

    fig.update_layout(
        height=max(600, 60 * data["display"].nunique()),
        bargap=0.2,
        legend_title_text="進捗",
        plot_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=40, b=40),
    )

    grid_mode = settings.get("grid_mode", "週")
    if grid_mode in {"週", "日"}:
        week_lines = make_week_lines(view_start, view_end)
        for line in week_lines:
            fig.add_vline(x=line, line=dict(color=GRID_COLOR, width=1, dash="dot"))
        if grid_mode == "日":
            for line in make_day_lines(view_start, view_end):
                fig.add_vline(x=line, line=dict(color="rgba(203, 213, 225, 0.5)", width=0.5))

    for span_start, _ in make_month_spans(view_start, view_end):
        fig.add_vline(x=span_start, line=dict(color="#111827", width=2))
    month_labels = make_month_labels(view_start, view_end)
    for x, label in month_labels:
        fig.add_annotation(
            x=x,
            y=1.02,
            xref="x",
            yref="paper",
            text=label,
            showarrow=False,
            font=dict(size=14, color="#1f2937"),
        )

    if settings.get("show_today", True):
        today = pd.Timestamp.now(tz="Asia/Tokyo").normalize()
        if view_start <= today <= view_end:
            fig.add_vline(x=today, line=dict(color="#ef4444", width=2))

    fig.update_layout(xaxis_title="日付", yaxis_title="案件")
    return fig
