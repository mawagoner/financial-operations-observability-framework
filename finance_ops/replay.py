"""Replay and state reconstruction helpers for operational observability."""

from __future__ import annotations

import pandas as pd


def get_system_snapshot(df: pd.DataFrame, timestamp: pd.Timestamp) -> pd.DataFrame:
    """Return latest known state per entity up to the given timestamp."""
    if df.empty:
        return df.copy()

    snapshot_time = pd.Timestamp(timestamp)
    history = df[df["timestamp"] <= snapshot_time].copy()
    if history.empty:
        return history

    snapshot = (
        history.sort_values(["entity_id", "timestamp"])
        .groupby("entity_id", as_index=False)
        .tail(1)
        .sort_values(["workflow_stage", "entity_id"])
        .reset_index(drop=True)
    )
    return snapshot


def reconstruct_entity_timeline(df: pd.DataFrame, entity_id: str) -> pd.DataFrame:
    """Reconstruct full event timeline for one entity."""
    if df.empty:
        return df.copy()
    return df[df["entity_id"] == entity_id].sort_values("timestamp").reset_index(drop=True)


def replay_operational_day(df: pd.DataFrame, timestamp: pd.Timestamp) -> pd.DataFrame:
    """Return all events for a selected day with cumulative flow counters."""
    if df.empty:
        return df.copy()

    day = pd.Timestamp(timestamp).floor("D")
    day_end = day + pd.Timedelta(days=1)

    events = df[(df["timestamp"] >= day) & (df["timestamp"] < day_end)].sort_values("timestamp").reset_index(drop=True)
    if events.empty:
        return events

    events = events.copy()
    events["event_index"] = range(1, len(events) + 1)
    events["cumulative_failures"] = (events["integration_status"] == "failed").cumsum()
    events["cumulative_anomalies"] = events["anomaly_flag"].astype(bool).cumsum()
    return events


def calculate_workflow_state(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate current workflow state distribution from latest entity events."""
    if df.empty:
        return pd.DataFrame(columns=["workflow_stage", "workflow_status", "entities"])

    latest = (
        df.sort_values(["entity_id", "timestamp"])
        .groupby("entity_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
    state = (
        latest.groupby(["workflow_stage", "workflow_status"], as_index=False)
        .agg(entities=("entity_id", "count"))
        .sort_values(["workflow_stage", "entities"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return state
