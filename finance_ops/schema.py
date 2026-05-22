"""Canonical event schema for finance operations observability."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

CANONICAL_COLUMNS = [
    "timestamp",
    "source_system",
    "entity_type",
    "entity_id",
    "customer_id",
    "workflow_stage",
    "workflow_status",
    "event_type",
    "transaction_amount",
    "payment_status",
    "risk_score",
    "esg_score",
    "region",
    "assigned_team",
    "latency_ms",
    "integration_status",
    "anomaly_flag",
    "notes",
]

REQUIRED_COLUMNS = [
    "timestamp",
    "source_system",
    "entity_type",
    "entity_id",
    "workflow_stage",
    "workflow_status",
    "event_type",
]

OPTIONAL_COLUMNS = [column for column in CANONICAL_COLUMNS if column not in REQUIRED_COLUMNS]

NUMERIC_COLUMNS = ["transaction_amount", "risk_score", "esg_score", "latency_ms"]

WORKFLOW_STAGES = [
    "intake",
    "underwriting",
    "compliance_review",
    "approval",
    "funding",
    "servicing",
    "collections",
    "reporting",
]

WORKFLOW_STATUS = [
    "queued",
    "in_progress",
    "completed",
    "delayed",
    "escalated",
    "failed",
    "cancelled",
]

PAYMENT_STATUS = ["not_applicable", "pending", "completed", "delayed", "failed"]

INTEGRATION_STATUS = ["healthy", "degraded", "failed", "recovering", "unknown"]

BOOLEAN_TRUE = {"true", "1", "yes", "y", "t"}


def get_required_columns() -> list[str]:
    """Return required canonical event columns."""
    return REQUIRED_COLUMNS.copy()


def get_optional_columns() -> list[str]:
    """Return optional canonical event columns."""
    return OPTIONAL_COLUMNS.copy()


def _normalize_text(value: Any) -> str:
    return str(value).strip()


def _normalize_slug(value: Any) -> str:
    text = _normalize_text(value).lower().replace("-", "_").replace(" ", "_")
    return "_".join(token for token in text.split("_") if token)


def validate_event_dataframe(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Validate event dataframe shape and coercion with user-friendly errors."""
    errors: list[str] = []

    if not isinstance(df, pd.DataFrame):
        return False, ["Input must be a pandas DataFrame."]

    if df.empty:
        return False, ["Event dataframe is empty."]

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return False, errors

    timestamp_values = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    if timestamp_values.isna().all():
        errors.append("Column 'timestamp' cannot be parsed as datetime.")

    for column in ["source_system", "entity_type", "entity_id", "workflow_stage", "workflow_status", "event_type"]:
        if df[column].astype(str).str.strip().eq("").all():
            errors.append(f"Column '{column}' cannot be empty for all rows.")

    for column in ["transaction_amount", "risk_score", "esg_score", "latency_ms"]:
        if column not in df.columns:
            continue
        coerced = pd.to_numeric(df[column], errors="coerce")
        if coerced.isna().all() and df[column].notna().any():
            errors.append(f"Column '{column}' cannot be coerced to numeric values.")

    if "workflow_stage" in df.columns:
        invalid_stage_mask = ~df["workflow_stage"].astype(str).map(_normalize_slug).isin(WORKFLOW_STAGES)
        if invalid_stage_mask.all():
            errors.append("Column 'workflow_stage' contains no recognizable canonical stages.")

    if "workflow_status" in df.columns:
        invalid_status_mask = ~df["workflow_status"].astype(str).map(_normalize_slug).isin(WORKFLOW_STATUS)
        if invalid_status_mask.all():
            errors.append("Column 'workflow_status' contains no recognizable canonical statuses.")

    return len(errors) == 0, errors


def normalize_event_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize event data to canonical schema and stable conventions."""
    is_valid, errors = validate_event_dataframe(df)
    if not is_valid:
        raise ValueError("Event validation failed: " + " | ".join(errors))

    frame = df.copy()
    for column in CANONICAL_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)

    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["source_system"] = frame["source_system"].map(_normalize_slug)
    frame["entity_type"] = frame["entity_type"].map(_normalize_slug)
    frame["entity_id"] = frame["entity_id"].map(_normalize_text)
    frame["customer_id"] = frame["customer_id"].fillna("unknown_customer").map(_normalize_text)

    frame["workflow_stage"] = frame["workflow_stage"].map(_normalize_slug)
    frame.loc[~frame["workflow_stage"].isin(WORKFLOW_STAGES), "workflow_stage"] = "intake"

    frame["workflow_status"] = frame["workflow_status"].map(_normalize_slug)
    frame.loc[~frame["workflow_status"].isin(WORKFLOW_STATUS), "workflow_status"] = "in_progress"

    frame["event_type"] = frame["event_type"].map(_normalize_slug)

    frame["payment_status"] = frame["payment_status"].fillna("not_applicable").map(_normalize_slug)
    frame.loc[~frame["payment_status"].isin(PAYMENT_STATUS), "payment_status"] = "not_applicable"

    frame["integration_status"] = frame["integration_status"].fillna("unknown").map(_normalize_slug)
    frame.loc[~frame["integration_status"].isin(INTEGRATION_STATUS), "integration_status"] = "unknown"

    frame["region"] = frame["region"].fillna("unknown_region").map(_normalize_text)
    frame["assigned_team"] = frame["assigned_team"].fillna("unassigned").map(_normalize_text)

    frame["notes"] = frame["notes"].fillna("").map(lambda value: _normalize_text(value)[:280])

    frame["transaction_amount"] = frame["transaction_amount"].fillna(0.0)
    frame["risk_score"] = frame["risk_score"].fillna(frame["risk_score"].median() if frame["risk_score"].notna().any() else 50.0)
    frame["esg_score"] = frame["esg_score"].fillna(frame["esg_score"].median() if frame["esg_score"].notna().any() else 60.0)
    frame["latency_ms"] = frame["latency_ms"].fillna(frame["latency_ms"].median() if frame["latency_ms"].notna().any() else 240.0)

    frame["risk_score"] = frame["risk_score"].clip(0.0, 100.0)
    frame["esg_score"] = frame["esg_score"].clip(0.0, 100.0)
    frame["latency_ms"] = frame["latency_ms"].clip(lower=0.0)

    anomaly_raw = frame["anomaly_flag"].fillna(False)
    frame["anomaly_flag"] = anomaly_raw.map(lambda value: str(value).strip().lower() in BOOLEAN_TRUE if not isinstance(value, bool) else value)

    required_subset = REQUIRED_COLUMNS + ["timestamp"]
    frame = frame.dropna(subset=required_subset)

    if frame.empty:
        raise ValueError(
            "No valid events remain after normalization. "
            "Check timestamps and required operational fields."
        )

    frame = frame.sort_values(["timestamp", "entity_id", "event_type"]).reset_index(drop=True)
    return frame[CANONICAL_COLUMNS]


def describe_schema() -> dict[str, Any]:
    """Return schema metadata for docs and debugging."""
    return {
        "canonical_columns": CANONICAL_COLUMNS.copy(),
        "required_columns": REQUIRED_COLUMNS.copy(),
        "optional_columns": OPTIONAL_COLUMNS.copy(),
        "numeric_columns": NUMERIC_COLUMNS.copy(),
        "workflow_stages": WORKFLOW_STAGES.copy(),
        "workflow_status": WORKFLOW_STATUS.copy(),
    }
