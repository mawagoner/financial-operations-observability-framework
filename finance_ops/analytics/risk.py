"""Risk analytics for operational finance event streams."""

from __future__ import annotations

import numpy as np
import pandas as pd


def summarize_risk_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Return binned distribution of risk scores."""
    if df.empty:
        return pd.DataFrame(columns=["risk_band", "events", "share"])

    bins = [0, 20, 40, 60, 75, 90, 100]
    labels = ["0-20", "21-40", "41-60", "61-75", "76-90", "91-100"]
    working = df.copy()
    working["risk_band"] = pd.cut(working["risk_score"], bins=bins, labels=labels, include_lowest=True)
    summary = (
        working.groupby("risk_band", observed=True, as_index=False)
        .agg(events=("timestamp", "count"))
        .sort_values("risk_band")
        .reset_index(drop=True)
    )
    total = max(1, int(summary["events"].sum()))
    summary["share"] = (summary["events"] / float(total)).round(4)
    return summary


def detect_high_risk_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Detect operational clusters with concentrated high-risk events."""
    if df.empty:
        return pd.DataFrame(columns=["region", "assigned_team", "high_risk_events", "customers", "mean_risk_score", "severity"])

    high_risk = df[df["risk_score"] >= 75.0].copy()
    if high_risk.empty:
        return pd.DataFrame(columns=["region", "assigned_team", "high_risk_events", "customers", "mean_risk_score", "severity"])

    clusters = (
        high_risk.groupby(["region", "assigned_team"], as_index=False)
        .agg(
            high_risk_events=("timestamp", "count"),
            customers=("customer_id", "nunique"),
            mean_risk_score=("risk_score", "mean"),
        )
        .sort_values("high_risk_events", ascending=False)
        .reset_index(drop=True)
    )

    baseline = max(float(clusters["high_risk_events"].median()), 1.0)
    clusters["severity"] = ((clusters["high_risk_events"] / baseline) * (clusters["mean_risk_score"] / 80.0)).round(3)
    return clusters


def compare_regions_by_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Compare risk posture across regions."""
    if df.empty:
        return pd.DataFrame(columns=["region", "events", "avg_risk_score", "p90_risk_score", "high_risk_share"])

    summary = (
        df.groupby("region", as_index=False)
        .agg(
            events=("timestamp", "count"),
            avg_risk_score=("risk_score", "mean"),
            p90_risk_score=("risk_score", lambda values: float(np.percentile(values, 90))),
            high_risk_share=("risk_score", lambda values: float((values >= 75.0).mean())),
        )
        .sort_values("avg_risk_score", ascending=False)
        .reset_index(drop=True)
    )
    summary[["avg_risk_score", "p90_risk_score", "high_risk_share"]] = summary[
        ["avg_risk_score", "p90_risk_score", "high_risk_share"]
    ].round(4)
    return summary


def track_risk_changes_over_time(df: pd.DataFrame) -> pd.DataFrame:
    """Track risk trend over time windows for observability timelines."""
    if df.empty:
        return pd.DataFrame(columns=["date", "avg_risk_score", "p90_risk_score", "high_risk_events"])

    working = df.copy()
    working["date"] = pd.to_datetime(working["timestamp"]).dt.floor("D")
    trend = (
        working.groupby("date", as_index=False)
        .agg(
            avg_risk_score=("risk_score", "mean"),
            p90_risk_score=("risk_score", lambda values: float(np.percentile(values, 90))),
            high_risk_events=("risk_score", lambda values: int((values >= 75.0).sum())),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    trend[["avg_risk_score", "p90_risk_score"]] = trend[["avg_risk_score", "p90_risk_score"]].round(3)
    return trend
