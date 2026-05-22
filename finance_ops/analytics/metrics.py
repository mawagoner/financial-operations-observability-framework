"""KPI and aggregation metrics for finance operations observability."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..utils import safe_ratio


def _payment_events(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["payment_status"] != "not_applicable") | (df["entity_type"] == "payment")].copy()


def summarize_kpis(df: pd.DataFrame) -> dict[str, float]:
    """Compute headline KPI values for operational observability cards."""
    if df.empty:
        return {
            "total_events": 0.0,
            "unique_entities": 0.0,
            "unique_customers": 0.0,
            "payment_completion_rate": 0.0,
            "workflow_completion_rate": 0.0,
            "avg_workflow_completion_hours": 0.0,
            "average_risk_score": 0.0,
            "average_esg_score": 0.0,
            "avg_latency_ms": 0.0,
            "integration_failure_count": 0.0,
            "anomaly_count": 0.0,
            "delayed_payment_percentage": 0.0,
        }

    payment_events = _payment_events(df)
    completed_payments = int((payment_events["payment_status"] == "completed").sum())
    delayed_payments = int((payment_events["payment_status"] == "delayed").sum())

    workflow_entities = df.groupby("entity_id", as_index=False).agg(
        first_seen=("timestamp", "min"),
        last_seen=("timestamp", "max"),
        has_completed=("workflow_status", lambda values: bool((values == "completed").any())),
    )
    completed_entities = workflow_entities[workflow_entities["has_completed"]]
    duration_hours = (
        (completed_entities["last_seen"] - completed_entities["first_seen"]).dt.total_seconds() / 3600.0
    )

    workflow_completion_rate = safe_ratio(float(len(completed_entities)), float(len(workflow_entities)))
    payment_completion_rate = safe_ratio(float(completed_payments), float(len(payment_events)))
    delayed_payment_percentage = safe_ratio(float(delayed_payments), float(len(payment_events)))

    return {
        "total_events": float(len(df)),
        "unique_entities": float(df["entity_id"].nunique()),
        "unique_customers": float(df["customer_id"].nunique()),
        "payment_completion_rate": payment_completion_rate,
        "workflow_completion_rate": workflow_completion_rate,
        "avg_workflow_completion_hours": float(duration_hours.mean()) if not duration_hours.empty else 0.0,
        "average_risk_score": float(df["risk_score"].mean()),
        "average_esg_score": float(df["esg_score"].mean()),
        "avg_latency_ms": float(df["latency_ms"].mean()),
        "integration_failure_count": float((df["integration_status"] == "failed").sum()),
        "anomaly_count": float(df["anomaly_flag"].sum()),
        "delayed_payment_percentage": delayed_payment_percentage,
    }


def summarize_by_workflow_stage(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize operational performance by workflow stage."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "workflow_stage",
                "events",
                "unique_entities",
                "completion_rate",
                "avg_latency_ms",
                "avg_risk_score",
                "avg_esg_score",
            ]
        )

    summary = (
        df.groupby("workflow_stage", as_index=False)
        .agg(
            events=("timestamp", "count"),
            unique_entities=("entity_id", "nunique"),
            completion_rate=("workflow_status", lambda values: float((values == "completed").mean())),
            avg_latency_ms=("latency_ms", "mean"),
            avg_risk_score=("risk_score", "mean"),
            avg_esg_score=("esg_score", "mean"),
        )
        .sort_values("events", ascending=False)
        .reset_index(drop=True)
    )
    numeric_columns = ["completion_rate", "avg_latency_ms", "avg_risk_score", "avg_esg_score"]
    summary[numeric_columns] = summary[numeric_columns].round(4)
    return summary


def summarize_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize operational metrics by region."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "region",
                "events",
                "customers",
                "avg_latency_ms",
                "avg_risk_score",
                "avg_esg_score",
                "integration_failures",
                "anomaly_events",
            ]
        )

    summary = (
        df.groupby("region", as_index=False)
        .agg(
            events=("timestamp", "count"),
            customers=("customer_id", "nunique"),
            avg_latency_ms=("latency_ms", "mean"),
            avg_risk_score=("risk_score", "mean"),
            avg_esg_score=("esg_score", "mean"),
            integration_failures=("integration_status", lambda values: int((values == "failed").sum())),
            anomaly_events=("anomaly_flag", "sum"),
        )
        .sort_values("events", ascending=False)
        .reset_index(drop=True)
    )
    numeric_columns = ["avg_latency_ms", "avg_risk_score", "avg_esg_score"]
    summary[numeric_columns] = summary[numeric_columns].round(3)
    summary["anomaly_events"] = summary["anomaly_events"].astype(int)
    return summary


def summarize_by_team(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize operational load and quality by assigned team."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "assigned_team",
                "events",
                "entities",
                "completion_rate",
                "avg_latency_ms",
                "escalation_events",
                "integration_failures",
            ]
        )

    summary = (
        df.groupby("assigned_team", as_index=False)
        .agg(
            events=("timestamp", "count"),
            entities=("entity_id", "nunique"),
            completion_rate=("workflow_status", lambda values: float((values == "completed").mean())),
            avg_latency_ms=("latency_ms", "mean"),
            escalation_events=("workflow_status", lambda values: int((values == "escalated").sum())),
            integration_failures=("integration_status", lambda values: int((values == "failed").sum())),
        )
        .sort_values("events", ascending=False)
        .reset_index(drop=True)
    )
    summary[["completion_rate", "avg_latency_ms"]] = summary[["completion_rate", "avg_latency_ms"]].round(4)
    return summary


def summarize_payment_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Return payment-centric operational summary metrics."""
    payment_events = _payment_events(df)
    if payment_events.empty:
        return {
            "payment_events": 0.0,
            "completion_rate": 0.0,
            "delayed_rate": 0.0,
            "failed_rate": 0.0,
            "total_amount": 0.0,
            "avg_payment_amount": 0.0,
            "collections_escalations": 0.0,
        }

    total_events = float(len(payment_events))
    completion_rate = safe_ratio(float((payment_events["payment_status"] == "completed").sum()), total_events)
    delayed_rate = safe_ratio(float((payment_events["payment_status"] == "delayed").sum()), total_events)
    failed_rate = safe_ratio(float((payment_events["payment_status"] == "failed").sum()), total_events)
    collections_escalations = float((payment_events["event_type"] == "collections_escalation").sum())

    return {
        "payment_events": total_events,
        "completion_rate": completion_rate,
        "delayed_rate": delayed_rate,
        "failed_rate": failed_rate,
        "total_amount": float(payment_events["transaction_amount"].sum()),
        "avg_payment_amount": float(payment_events["transaction_amount"].mean()),
        "collections_escalations": collections_escalations,
    }


def summarize_operational_latency(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize latency distribution by source system and workflow stage."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "source_system",
                "workflow_stage",
                "events",
                "p50_latency_ms",
                "p90_latency_ms",
                "p99_latency_ms",
                "avg_latency_ms",
            ]
        )

    grouped = (
        df.groupby(["source_system", "workflow_stage"], as_index=False)
        .agg(
            events=("timestamp", "count"),
            p50_latency_ms=("latency_ms", lambda values: float(np.percentile(values, 50))),
            p90_latency_ms=("latency_ms", lambda values: float(np.percentile(values, 90))),
            p99_latency_ms=("latency_ms", lambda values: float(np.percentile(values, 99))),
            avg_latency_ms=("latency_ms", "mean"),
        )
        .sort_values("p90_latency_ms", ascending=False)
        .reset_index(drop=True)
    )

    numeric_columns = ["p50_latency_ms", "p90_latency_ms", "p99_latency_ms", "avg_latency_ms"]
    grouped[numeric_columns] = grouped[numeric_columns].round(2)
    return grouped
