"""Data import/export helpers."""
from __future__ import annotations

import io
import json
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from .dates import to_timestamp, validate_range

DEFAULT_COLOR = "#f97316"


@dataclass
class ImportResult:
    """Result of a data import operation."""

    projects: pd.DataFrame
    segments: pd.DataFrame


REQUIRED_COLUMNS = [
    "name",
    "client",
    "site",
    "work_type",
    "owner",
    "progress",
    "start_date",
    "end_date",
]


def load_sample_data(csv_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load the bundled CSV and create project/segment frames."""
    raw = pd.read_csv(csv_path)
    projects_rows: List[Dict[str, str]] = []
    segments_rows: List[Dict[str, str]] = []
    for idx, row in raw.iterrows():
        project_id = f"PRJ-{idx+1:03d}"
        projects_rows.append(
            {
                "id": project_id,
                "name": row["name"],
                "client": row["client"],
                "site": row["site"],
                "work_type": row["work_type"],
                "owner": row["owner"],
                "progress": row["progress"],
                "note": "",
                "color": DEFAULT_COLOR,
            }
        )
        segments_rows.append(
            {
                "segment_id": str(uuid.uuid4()),
                "project_id": project_id,
                "label": "基本工期",
                "start_date": row["start_date"],
                "end_date": row["end_date"],
            }
        )

    # Add a couple of milestone segments for demonstration purposes.
    if projects_rows:
        first_project = projects_rows[0]["id"]
        segments_rows.append(
            {
                "segment_id": str(uuid.uuid4()),
                "project_id": first_project,
                "label": "内装工事",
                "start_date": "2025-08-20",
                "end_date": "2025-09-05",
            }
        )
    if len(projects_rows) > 3:
        logistics_project = projects_rows[3]["id"]
        segments_rows.append(
            {
                "segment_id": str(uuid.uuid4()),
                "project_id": logistics_project,
                "label": "設備搬入",
                "start_date": "2026-02-01",
                "end_date": "2026-02-15",
            }
        )

    projects_df = pd.DataFrame(projects_rows)
    segments_df = pd.DataFrame(segments_rows)
    projects_df["id"] = projects_df["id"].astype(str)
    segments_df["project_id"] = segments_df["project_id"].astype(str)
    for col in ("start_date", "end_date"):
        segments_df[col] = pd.to_datetime(segments_df[col])
    return projects_df, segments_df


def parse_uploaded_file(upload, file_format: str) -> pd.DataFrame:
    """Parse an uploaded CSV or JSON file into a DataFrame."""
    if upload is None:
        raise ValueError("ファイルが選択されていません")
    if file_format == "CSV":
        return pd.read_csv(upload)
    if file_format == "JSON":
        data = json.load(upload)
        return pd.DataFrame(data)
    raise ValueError("対応していないファイル形式です")


def transform_import(df: pd.DataFrame, mapping: Dict[str, str]) -> ImportResult:
    """Transform an imported DataFrame according to the provided mapping."""
    missing = [field for field in REQUIRED_COLUMNS if field not in mapping]
    if missing:
        raise ValueError("マッピングが未完了です")
    records = df.rename(columns=mapping)
    required_missing = [col for col in REQUIRED_COLUMNS if col not in records.columns]
    if required_missing:
        raise ValueError("必要な列が足りません")

    projects_rows: List[Dict[str, str]] = []
    segments_rows: List[Dict[str, str]] = []
    for idx, row in records.iterrows():
        start_ts, end_ts = validate_range(row["start_date"], row["end_date"])
        project_id = str(uuid.uuid4())
        projects_rows.append(
            {
                "id": project_id,
                "name": str(row["name"]),
                "client": str(row["client"]),
                "site": str(row["site"]),
                "work_type": str(row["work_type"]),
                "owner": str(row["owner"]),
                "progress": str(row["progress"]),
                "note": str(row.get("note", "")),
                "color": row.get("color", DEFAULT_COLOR) or DEFAULT_COLOR,
            }
        )
        segments_rows.append(
            {
                "segment_id": str(uuid.uuid4()),
                "project_id": project_id,
                "label": str(row.get("label", "工期")),
                "start_date": start_ts,
                "end_date": end_ts,
            }
        )

    projects_df = pd.DataFrame(projects_rows)
    segments_df = pd.DataFrame(segments_rows)
    return ImportResult(projects=projects_df, segments=segments_df)


def export_dataframe(
    projects_df: pd.DataFrame,
    segments_df: pd.DataFrame,
    project_ids: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Create a flat DataFrame suitable for CSV/JSON export."""
    segs = segments_df.copy()
    segs["start_date"] = segs["start_date"].apply(lambda x: to_timestamp(x).date().isoformat())
    segs["end_date"] = segs["end_date"].apply(lambda x: to_timestamp(x).date().isoformat())
    merged = segs.merge(projects_df, left_on="project_id", right_on="id", how="left", suffixes=("_seg", ""))
    if project_ids is not None:
        merged = merged[merged["project_id"].isin(project_ids)]
    columns = [
        "name",
        "client",
        "site",
        "work_type",
        "owner",
        "progress",
        "start_date",
        "end_date",
        "label",
        "note",
        "color",
    ]
    return merged[columns]


def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to CSV bytes."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")


def dataframe_to_json(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to JSON bytes."""
    return df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")
