"""Integration observability analytics for cross-system operations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def summarize_integration_health(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize integration health by source system."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "source_system",
                "events",
                "healthy_rate",
                "degraded_rate",
                "failed_rate",
                "avg_latency_ms",
                "p95_latency_ms",
            ]
        )

    summary = (
        df.groupby("source_system", as_index=False)
        .agg(
            events=("timestamp", "count"),
            healthy_rate=("integration_status", lambda values: float((values == "healthy").mean())),
            degraded_rate=("integration_status", lambda values: float((values == "degraded").mean())),
            failed_rate=("integration_status", lambda values: float((values == "failed").mean())),
            avg_latency_ms=("latency_ms", "mean"),
            p95_latency_ms=("latency_ms", lambda values: float(np.percentile(values, 95))),
        )
        .sort_values("failed_rate", ascending=False)
        .reset_index(drop=True)
    )
    numeric_columns = ["healthy_rate", "degraded_rate", "failed_rate", "avg_latency_ms", "p95_latency_ms"]
    summary[numeric_columns] = summary[numeric_columns].round(4)
    return summary


def detect_failed_integrations(df: pd.DataFrame) -> pd.DataFrame:
    """Return failed/degraded integration records ordered by severity."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "source_system",
                "entity_id",
                "integration_status",
                "latency_ms",
                "workflow_stage",
                "notes",
            ]
        )

    failures = df[df["integration_status"].isin(["failed", "degraded"])].copy()
    if failures.empty:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "source_system",
                "entity_id",
                "integration_status",
                "latency_ms",
                "workflow_stage",
                "notes",
            ]
        )

    failures["severity_rank"] = np.where(failures["integration_status"] == "failed", 2, 1)
    failures = failures.sort_values(["severity_rank", "latency_ms"], ascending=[False, False]).reset_index(drop=True)
    return failures[
        ["timestamp", "source_system", "entity_id", "integration_status", "latency_ms", "workflow_stage", "notes"]
    ]


def track_integration_latency(df: pd.DataFrame) -> pd.DataFrame:
    """Track latency over time for each source system."""
    if df.empty:
        return pd.DataFrame(columns=["date", "source_system", "avg_latency_ms", "p90_latency_ms", "events"])

    working = df.copy()
    working["date"] = pd.to_datetime(working["timestamp"]).dt.floor("D")
    trend = (
        working.groupby(["date", "source_system"], as_index=False)
        .agg(
            avg_latency_ms=("latency_ms", "mean"),
            p90_latency_ms=("latency_ms", lambda values: float(np.percentile(values, 90))),
            events=("timestamp", "count"),
        )
        .sort_values(["date", "source_system"])
        .reset_index(drop=True)
    )
    trend[["avg_latency_ms", "p90_latency_ms"]] = trend[["avg_latency_ms", "p90_latency_ms"]].round(3)
    return trend


def detect_synchronization_gaps(df: pd.DataFrame, gap_hours_threshold: float = 48.0) -> pd.DataFrame:
    """Detect cross-system synchronization gaps by customer and source."""
    if df.empty:
        return pd.DataFrame(columns=["customer_id", "source_system", "timestamp", "gap_hours", "workflow_stage", "notes"])

    working = df.sort_values(["customer_id", "source_system", "timestamp"]).copy()
    working["prev_timestamp"] = working.groupby(["customer_id", "source_system"])["timestamp"].shift(1)
    working["gap_hours"] = (working["timestamp"] - working["prev_timestamp"]).dt.total_seconds() / 3600.0
    gaps = working[working["gap_hours"] > float(gap_hours_threshold)].copy()
    if gaps.empty:
        return pd.DataFrame(columns=["customer_id", "source_system", "timestamp", "gap_hours", "workflow_stage", "notes"])

    return gaps[["customer_id", "source_system", "timestamp", "gap_hours", "workflow_stage", "notes"]].sort_values(
        "gap_hours", ascending=False
    ).reset_index(drop=True)
