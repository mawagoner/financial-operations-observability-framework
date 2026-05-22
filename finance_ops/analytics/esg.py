"""ESG and impact analytics for operations telemetry."""

from __future__ import annotations

import pandas as pd


def summarize_esg_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Return ESG score distribution bands."""
    if df.empty:
        return pd.DataFrame(columns=["esg_band", "events", "share"])

    bins = [0, 25, 50, 70, 85, 100]
    labels = ["0-25", "26-50", "51-70", "71-85", "86-100"]
    working = df.copy()
    working["esg_band"] = pd.cut(working["esg_score"], bins=bins, labels=labels, include_lowest=True)
    summary = (
        working.groupby("esg_band", observed=True, as_index=False)
        .agg(events=("timestamp", "count"))
        .sort_values("esg_band")
        .reset_index(drop=True)
    )
    total = max(1, int(summary["events"].sum()))
    summary["share"] = (summary["events"] / float(total)).round(4)
    return summary


def track_esg_changes_over_time(df: pd.DataFrame) -> pd.DataFrame:
    """Track ESG trends over daily windows."""
    if df.empty:
        return pd.DataFrame(columns=["date", "avg_esg_score", "min_esg_score", "max_esg_score"])

    working = df.copy()
    working["date"] = pd.to_datetime(working["timestamp"]).dt.floor("D")
    trend = (
        working.groupby("date", as_index=False)
        .agg(
            avg_esg_score=("esg_score", "mean"),
            min_esg_score=("esg_score", "min"),
            max_esg_score=("esg_score", "max"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    trend[["avg_esg_score", "min_esg_score", "max_esg_score"]] = trend[
        ["avg_esg_score", "min_esg_score", "max_esg_score"]
    ].round(3)
    return trend


def analyze_esg_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Compare ESG metrics by region."""
    if df.empty:
        return pd.DataFrame(columns=["region", "events", "avg_esg_score", "p10_esg_score", "p90_esg_score"])

    summary = (
        df.groupby("region", as_index=False)
        .agg(
            events=("timestamp", "count"),
            avg_esg_score=("esg_score", "mean"),
            p10_esg_score=("esg_score", lambda values: values.quantile(0.10)),
            p90_esg_score=("esg_score", lambda values: values.quantile(0.90)),
        )
        .sort_values("avg_esg_score", ascending=False)
        .reset_index(drop=True)
    )
    summary[["avg_esg_score", "p10_esg_score", "p90_esg_score"]] = summary[
        ["avg_esg_score", "p10_esg_score", "p90_esg_score"]
    ].round(3)
    return summary


def summarize_impact_scores(df: pd.DataFrame) -> dict[str, float]:
    """Return compact ESG/impact score summary for executive cards."""
    if df.empty:
        return {
            "average_esg_score": 0.0,
            "high_impact_share": 0.0,
            "low_impact_share": 0.0,
            "esg_update_events": 0.0,
        }

    esg_updates = df[df["event_type"].str.contains("esg", na=False)]
    return {
        "average_esg_score": float(df["esg_score"].mean()),
        "high_impact_share": float((df["esg_score"] >= 75.0).mean()),
        "low_impact_share": float((df["esg_score"] < 45.0).mean()),
        "esg_update_events": float(len(esg_updates)),
    }
