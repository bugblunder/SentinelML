"""Explicit input contracts shared by the CLI, dashboard and experiments."""

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED = ("event_time", "event_name", "principal_name")
OPTIONAL = (
    "ip_address",
    "source_service",
    "auth_type",
    "resource_name",
    "opc_client_info",
    "compartment_name",
)
MAX_ROWS = 100_000
MAX_BYTES = 25 * 1024 * 1024


class DataValidationError(ValueError):
    """Actionable input error, safe to display to an end user."""


@dataclass
class QualityReport:
    rows: int
    duplicate_events: int
    missing_optional: list[str]
    unknown_principals: int
    warnings: list[str]


def normalize_events(frame: pd.DataFrame) -> tuple[pd.DataFrame, QualityReport]:
    """Reject malformed required data; preserve row order and duplicate observations."""
    if frame.empty:
        raise DataValidationError("The CSV has no events.")
    if len(frame) > MAX_ROWS:
        raise DataValidationError(f"Use at most {MAX_ROWS:,} events per batch.")
    if not frame.columns.is_unique:
        raise DataValidationError("Column names must be unique.")
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise DataValidationError("Missing required columns: " + ", ".join(missing))
    df = frame.copy().reset_index(drop=True)
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce", utc=True, format="mixed")
    invalid = int(df["event_time"].isna().sum())
    if invalid:
        raise DataValidationError(f"{invalid} event_time value(s) are invalid. Use ISO 8601 timestamps.")
    missing_optional = [c for c in (*OPTIONAL, "response_status") if c not in df]
    for col in (*REQUIRED[1:], *OPTIONAL):
        if col not in df:
            df[col] = "unknown"
        df[col] = df[col].fillna("unknown").astype(str).str.strip().replace("", "unknown")
        if df[col].str.len().gt(2048).any():
            raise DataValidationError(f"{col} contains a value longer than 2,048 characters.")
    if df["event_name"].eq("unknown").any():
        raise DataValidationError("Every event requires a non-empty event_name.")
    if "response_status" not in df:
        df["response_status"] = 0
    else:
        status = pd.to_numeric(df["response_status"], errors="coerce")
        invalid_status = status.isna() | (status % 1 != 0) | ~((status == 0) | status.between(100, 599))
        if invalid_status.any():
            raise DataValidationError(
                "response_status must be an integer HTTP status (100–599), or 0 for unknown."
            )
        df["response_status"] = status.astype(int)
    identity_cols = [*REQUIRED, *OPTIONAL, "response_status"]
    fingerprints = (
        df[identity_cols]
        .astype(str)
        .apply(
            lambda row: hashlib.sha256(json.dumps(row.tolist(), ensure_ascii=False).encode()).hexdigest()[
                :20
            ],
            axis=1,
        )
    )
    duplicates = int(fingerprints.duplicated().sum())
    # A source event ID is part of the audit trail; never silently overwrite it.
    if "event_id" in df:
        if df["event_id"].isna().any() or df["event_id"].astype(str).str.strip().eq("").any():
            raise DataValidationError("event_id must be non-empty when supplied.")
        df["event_id"] = df["event_id"].astype(str)
        if df["event_id"].duplicated().any():
            raise DataValidationError("event_id must be unique when supplied.")
    else:
        occurrence = fingerprints.groupby(fingerprints).cumcount().astype(str)
        df["event_id"] = fingerprints + "-" + occurrence
    warnings = []
    if duplicates:
        warnings.append(
            f"{duplicates} duplicate event payload(s) retained; duplicates can inflate burst counts."
        )
    if missing_optional:
        warnings.append("Optional fields filled with unknown: " + ", ".join(missing_optional))
    unknown = int(df["principal_name"].eq("unknown").sum())
    if unknown:
        warnings.append(
            f"{unknown} event(s) have unknown principals; principal-based burst rules are disabled for these events."
        )
    if df["response_status"].eq(0).any():
        warnings.append("Unknown response statuses cannot contribute to failed-authentication rules.")
    return df, QualityReport(len(df), duplicates, missing_optional, unknown, warnings)


def read_events(source) -> tuple[pd.DataFrame, QualityReport]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.stat().st_size > MAX_BYTES:
            raise DataValidationError("CSV exceeds the 25 MiB limit.")
        raw = path.read_bytes()
    elif isinstance(source, bytes):
        raw = source
    else:
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise DataValidationError("CSV exceeds the 25 MiB limit.")
    try:
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
        header = next(csv.reader(io.StringIO(text)), [])
        if len(header) != len(set(header)):
            raise DataValidationError("CSV contains duplicate column names.")
        frame = pd.read_csv(io.StringIO(text), nrows=MAX_ROWS + 1, dtype={"event_id": str})
    except (UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DataValidationError("Provide a valid UTF-8 CSV with a header row.") from exc
    return normalize_events(frame)
