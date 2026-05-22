"""Reporting-focused summaries for investor and audit workflows."""

from __future__ import annotations

import pandas as pd


def summarize_investor_reporting(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize investor reporting feed events by region and period."""
    reporting = df[
        (df["source_system"] == "investor_reporting_feed")
        | (df["event_type"].str.contains("report", na=False))
    ].copy()
    if reporting.empty:
        return pd.DataFrame(columns=["period", "region", "events", "total_reported_amount", "avg_risk_score", "avg_esg_score"])

    reporting["period"] = pd.to_datetime(reporting["timestamp"]).dt.to_period("W").astype(str)
    summary = (
        reporting.groupby(["period", "region"], as_index=False)
        .agg(
            events=("timestamp", "count"),
            total_reported_amount=("transaction_amount", "sum"),
            avg_risk_score=("risk_score", "mean"),
            avg_esg_score=("esg_score", "mean"),
        )
        .sort_values(["period", "events"], ascending=[True, False])
        .reset_index(drop=True)
    )
    summary[["total_reported_amount", "avg_risk_score", "avg_esg_score"]] = summary[
        ["total_reported_amount", "avg_risk_score", "avg_esg_score"]
    ].round(2)
    return summary


def summarize_operational_exports(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize report/export style events across source systems."""
    export_mask = df["event_type"].str.contains("report|export|snapshot", na=False)
    exports = df[export_mask].copy()
    if exports.empty:
        return pd.DataFrame(columns=["source_system", "event_type", "events", "avg_latency_ms", "anomaly_events"])

    summary = (
        exports.groupby(["source_system", "event_type"], as_index=False)
        .agg(
            events=("timestamp", "count"),
            avg_latency_ms=("latency_ms", "mean"),
            anomaly_events=("anomaly_flag", "sum"),
        )
        .sort_values("events", ascending=False)
        .reset_index(drop=True)
    )
    summary["avg_latency_ms"] = summary["avg_latency_ms"].round(2)
    summary["anomaly_events"] = summary["anomaly_events"].astype(int)
    return summary


def build_audit_event_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build audit-style daily summary of event quality and status."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "events",
                "failed_integrations",
                "delayed_or_failed_workflows",
                "anomaly_events",
                "avg_latency_ms",
            ]
        )

    working = df.copy()
    working["date"] = pd.to_datetime(working["timestamp"]).dt.floor("D")
    summary = (
        working.groupby("date", as_index=False)
        .agg(
            events=("timestamp", "count"),
            failed_integrations=("integration_status", lambda values: int((values == "failed").sum())),
            delayed_or_failed_workflows=(
                "workflow_status",
                lambda values: int(values.isin(["delayed", "failed", "escalated"]).sum()),
            ),
            anomaly_events=("anomaly_flag", "sum"),
            avg_latency_ms=("latency_ms", "mean"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    summary["anomaly_events"] = summary["anomaly_events"].astype(int)
    summary["avg_latency_ms"] = summary["avg_latency_ms"].round(2)
    return summary
