"""Payment and collections analytics."""

from __future__ import annotations

import pandas as pd


def _payment_events(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["payment_status"] != "not_applicable") | (df["entity_type"] == "payment")].copy()


def build_payment_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Build daily payment timeline with completion and exception counts."""
    payments = _payment_events(df)
    if payments.empty:
        return pd.DataFrame(columns=["date", "completed", "delayed", "failed", "total_amount"])

    payments["date"] = pd.to_datetime(payments["timestamp"]).dt.floor("D")
    timeline = (
        payments.groupby("date", as_index=False)
        .agg(
            completed=("payment_status", lambda values: int((values == "completed").sum())),
            delayed=("payment_status", lambda values: int((values == "delayed").sum())),
            failed=("payment_status", lambda values: int((values == "failed").sum())),
            total_amount=("transaction_amount", "sum"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    timeline["total_amount"] = timeline["total_amount"].round(2)
    return timeline


def summarize_delinquency(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize delinquency rates by region and team."""
    payments = _payment_events(df)
    if payments.empty:
        return pd.DataFrame(columns=["region", "assigned_team", "payment_events", "delinquent_events", "delinquency_rate"])

    summary = (
        payments.groupby(["region", "assigned_team"], as_index=False)
        .agg(
            payment_events=("timestamp", "count"),
            delinquent_events=("payment_status", lambda values: int(values.isin(["delayed", "failed"]).sum())),
        )
        .sort_values("delinquent_events", ascending=False)
        .reset_index(drop=True)
    )
    summary["delinquency_rate"] = (
        summary["delinquent_events"] / summary["payment_events"].replace(0, 1)
    ).round(4)
    return summary


def summarize_payment_completion(df: pd.DataFrame) -> dict[str, float]:
    """Return compact payment completion metrics."""
    payments = _payment_events(df)
    if payments.empty:
        return {
            "total_payment_events": 0.0,
            "completed_rate": 0.0,
            "delayed_rate": 0.0,
            "failed_rate": 0.0,
        }

    total = float(len(payments))
    return {
        "total_payment_events": total,
        "completed_rate": float((payments["payment_status"] == "completed").sum()) / total,
        "delayed_rate": float((payments["payment_status"] == "delayed").sum()) / total,
        "failed_rate": float((payments["payment_status"] == "failed").sum()) / total,
    }


def analyze_payment_delays(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze delayed payment patterns and associated latency/risk."""
    payments = _payment_events(df)
    delays = payments[payments["payment_status"] == "delayed"].copy()
    if delays.empty:
        return pd.DataFrame(columns=["region", "delay_events", "avg_latency_ms", "avg_risk_score", "avg_amount"])

    summary = (
        delays.groupby("region", as_index=False)
        .agg(
            delay_events=("timestamp", "count"),
            avg_latency_ms=("latency_ms", "mean"),
            avg_risk_score=("risk_score", "mean"),
            avg_amount=("transaction_amount", "mean"),
        )
        .sort_values("delay_events", ascending=False)
        .reset_index(drop=True)
    )
    summary[["avg_latency_ms", "avg_risk_score", "avg_amount"]] = summary[
        ["avg_latency_ms", "avg_risk_score", "avg_amount"]
    ].round(3)
    return summary


def summarize_collections_escalations(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize collections escalation events for operations teams."""
    escalations = df[
        (df["workflow_stage"] == "collections")
        & ((df["event_type"] == "collections_escalation") | (df["workflow_status"] == "escalated"))
    ].copy()

    if escalations.empty:
        return pd.DataFrame(columns=["assigned_team", "region", "escalation_events", "avg_risk_score", "avg_latency_ms"])

    summary = (
        escalations.groupby(["assigned_team", "region"], as_index=False)
        .agg(
            escalation_events=("timestamp", "count"),
            avg_risk_score=("risk_score", "mean"),
            avg_latency_ms=("latency_ms", "mean"),
        )
        .sort_values("escalation_events", ascending=False)
        .reset_index(drop=True)
    )
    summary[["avg_risk_score", "avg_latency_ms"]] = summary[["avg_risk_score", "avg_latency_ms"]].round(3)
    return summary
