"""Workflow reconstruction and bottleneck analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def reconstruct_workflow_timeline(df: pd.DataFrame, entity_id: str) -> pd.DataFrame:
    """Return chronological workflow timeline for an entity."""
    if df.empty:
        return pd.DataFrame(columns=df.columns)
    timeline = df[df["entity_id"] == entity_id].sort_values("timestamp").reset_index(drop=True)
    return timeline


def summarize_workflow_transitions(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize observed stage-to-stage transitions across entities."""
    if df.empty:
        return pd.DataFrame(columns=["from_stage", "to_stage", "transition_count", "share"])

    working = df.sort_values(["entity_id", "timestamp"]).copy()
    working["next_stage"] = working.groupby("entity_id")["workflow_stage"].shift(-1)
    transitions = working.dropna(subset=["next_stage"]).copy()
    transitions = transitions[transitions["workflow_stage"] != transitions["next_stage"]]

    if transitions.empty:
        return pd.DataFrame(columns=["from_stage", "to_stage", "transition_count", "share"])

    summary = (
        transitions.groupby(["workflow_stage", "next_stage"], as_index=False)
        .agg(transition_count=("entity_id", "count"))
        .rename(columns={"workflow_stage": "from_stage", "next_stage": "to_stage"})
        .sort_values("transition_count", ascending=False)
        .reset_index(drop=True)
    )
    total = max(1, int(summary["transition_count"].sum()))
    summary["share"] = summary["transition_count"] / float(total)
    summary["share"] = summary["share"].round(4)
    return summary


def calculate_stage_durations(df: pd.DataFrame) -> pd.DataFrame:
    """Estimate stage durations from sequential events per entity."""
    if df.empty:
        return pd.DataFrame(
            columns=["workflow_stage", "sample_pairs", "avg_duration_hours", "median_duration_hours", "p90_duration_hours"]
        )

    working = df.sort_values(["entity_id", "timestamp"]).copy()
    working["next_timestamp"] = working.groupby("entity_id")["timestamp"].shift(-1)
    working["duration_hours"] = (
        (working["next_timestamp"] - working["timestamp"]).dt.total_seconds() / 3600.0
    )
    durations = working[(working["duration_hours"].notna()) & (working["duration_hours"] >= 0.0)].copy()

    if durations.empty:
        return pd.DataFrame(
            columns=["workflow_stage", "sample_pairs", "avg_duration_hours", "median_duration_hours", "p90_duration_hours"]
        )

    summary = (
        durations.groupby("workflow_stage", as_index=False)
        .agg(
            sample_pairs=("duration_hours", "count"),
            avg_duration_hours=("duration_hours", "mean"),
            median_duration_hours=("duration_hours", "median"),
            p90_duration_hours=("duration_hours", lambda values: float(np.percentile(values, 90))),
        )
        .sort_values("avg_duration_hours", ascending=False)
        .reset_index(drop=True)
    )

    numeric_columns = ["avg_duration_hours", "median_duration_hours", "p90_duration_hours"]
    summary[numeric_columns] = summary[numeric_columns].round(3)
    return summary


def detect_bottlenecks(df: pd.DataFrame) -> pd.DataFrame:
    """Detect likely bottleneck stages using duration and escalation heuristics."""
    durations = calculate_stage_durations(df)
    if durations.empty:
        return pd.DataFrame(
            columns=[
                "workflow_stage",
                "avg_duration_hours",
                "p90_duration_hours",
                "delay_or_escalation_rate",
                "severity",
                "explanation",
            ]
        )

    status_summary = (
        df.groupby("workflow_stage", as_index=False)
        .agg(
            events=("timestamp", "count"),
            delayed_or_escalated=(
                "workflow_status",
                lambda values: int(values.isin(["delayed", "escalated", "failed"]).sum()),
            ),
        )
        .reset_index(drop=True)
    )
    status_summary["delay_or_escalation_rate"] = (
        status_summary["delayed_or_escalated"] / status_summary["events"].replace(0, 1)
    )

    merged = durations.merge(status_summary[["workflow_stage", "delay_or_escalation_rate"]], on="workflow_stage", how="left")
    merged["delay_or_escalation_rate"] = merged["delay_or_escalation_rate"].fillna(0.0)

    avg_baseline = max(float(merged["avg_duration_hours"].median()), 0.1)
    p90_baseline = max(float(merged["p90_duration_hours"].median()), 0.1)

    merged["severity"] = (
        0.55 * (merged["avg_duration_hours"] / avg_baseline)
        + 0.30 * (merged["p90_duration_hours"] / p90_baseline)
        + 0.15 * (merged["delay_or_escalation_rate"] / max(float(merged["delay_or_escalation_rate"].median()), 0.01))
    )
    merged["severity"] = merged["severity"].clip(0.0, 5.0).round(3)

    merged["explanation"] = merged.apply(
        lambda row: (
            f"Stage shows elevated cycle time ({row['avg_duration_hours']:.1f}h avg) "
            f"and {row['delay_or_escalation_rate']:.1%} delayed/escalated events."
        ),
        axis=1,
    )

    return merged[
        [
            "workflow_stage",
            "avg_duration_hours",
            "p90_duration_hours",
            "delay_or_escalation_rate",
            "severity",
            "explanation",
        ]
    ].sort_values("severity", ascending=False).reset_index(drop=True)
