"""Reusable Plotly visualizations for finance operations observability."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .analytics.integrations import summarize_integration_health, track_integration_latency
from .analytics.payments import build_payment_timeline
from .analytics.risk import summarize_risk_distribution

PALETTE = {
    "ink": "#163248",
    "teal": "#2d728f",
    "amber": "#d98f3f",
    "green": "#2d936c",
    "red": "#b23a48",
    "steel": "#5c738a",
    "sand": "#e8ddc5",
}


def _base_layout(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=title,
        height=height,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "IBM Plex Sans, Segoe UI, sans-serif", "color": "#1f2933"},
    )
    return fig


def plot_workflow_pipeline(df: pd.DataFrame) -> go.Figure:
    """Plot event volume by workflow stage and status."""
    if df.empty:
        return _base_layout(go.Figure(), "Workflow Pipeline")

    stage_counts = (
        df.groupby(["workflow_stage", "workflow_status"], as_index=False)
        .agg(events=("timestamp", "count"))
        .sort_values("events", ascending=False)
    )

    fig = px.bar(
        stage_counts,
        x="workflow_stage",
        y="events",
        color="workflow_status",
        title="Workflow Pipeline by Stage and Status",
        color_discrete_sequence=[PALETTE["teal"], PALETTE["green"], PALETTE["amber"], PALETTE["red"], PALETTE["steel"]],
    )
    fig.update_xaxes(title="Workflow Stage")
    fig.update_yaxes(title="Events")
    return _base_layout(fig, "Workflow Pipeline")


def plot_operational_timeline(df: pd.DataFrame) -> go.Figure:
    """Plot daily event volume by source system."""
    if df.empty:
        return _base_layout(go.Figure(), "Operational Timeline")

    timeline = df.copy()
    timeline["date"] = pd.to_datetime(timeline["timestamp"]).dt.floor("D")
    summary = timeline.groupby(["date", "source_system"], as_index=False).agg(events=("timestamp", "count"))

    fig = px.line(
        summary,
        x="date",
        y="events",
        color="source_system",
        title="Operational Timeline by Source System",
        line_shape="spline",
    )
    fig.update_yaxes(title="Events")
    fig.update_xaxes(title="Date")
    return _base_layout(fig, "Operational Timeline", height=360)


def plot_payment_flow(df: pd.DataFrame) -> go.Figure:
    """Plot payment flow outcomes over time."""
    timeline = build_payment_timeline(df)
    if timeline.empty:
        return _base_layout(go.Figure(), "Payment Flow")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=timeline["date"], y=timeline["completed"], name="Completed", marker_color=PALETTE["green"]))
    fig.add_trace(go.Bar(x=timeline["date"], y=timeline["delayed"], name="Delayed", marker_color=PALETTE["amber"]))
    fig.add_trace(go.Bar(x=timeline["date"], y=timeline["failed"], name="Failed", marker_color=PALETTE["red"]))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Date")
    fig.update_yaxes(title="Payment Events")
    return _base_layout(fig, "Payment Flow", height=360)


def plot_risk_distribution(df: pd.DataFrame) -> go.Figure:
    """Plot risk score distribution."""
    bands = summarize_risk_distribution(df)
    if bands.empty:
        return _base_layout(go.Figure(), "Risk Distribution")

    fig = px.bar(
        bands,
        x="risk_band",
        y="events",
        title="Risk Score Distribution",
        color="risk_band",
        color_discrete_sequence=[PALETTE["green"], PALETTE["teal"], PALETTE["steel"], PALETTE["amber"], PALETTE["red"], "#6e2f45"],
    )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title="Risk Band")
    fig.update_yaxes(title="Events")
    return _base_layout(fig, "Risk Distribution", height=340)


def plot_latency_over_time(df: pd.DataFrame) -> go.Figure:
    """Plot average and p90 integration latency over time."""
    trend = track_integration_latency(df)
    if trend.empty:
        return _base_layout(go.Figure(), "Operational Latency")

    fig = px.line(
        trend,
        x="date",
        y="p90_latency_ms",
        color="source_system",
        title="P90 Integration Latency Over Time",
        line_shape="spline",
    )
    fig.update_xaxes(title="Date")
    fig.update_yaxes(title="P90 Latency (ms)")
    return _base_layout(fig, "Operational Latency", height=370)


def plot_integration_health(df: pd.DataFrame) -> go.Figure:
    """Plot integration health rates by source system."""
    health = summarize_integration_health(df)
    if health.empty:
        return _base_layout(go.Figure(), "Integration Health")

    melted = health.melt(
        id_vars=["source_system"],
        value_vars=["healthy_rate", "degraded_rate", "failed_rate"],
        var_name="metric",
        value_name="value",
    )
    fig = px.bar(
        melted,
        x="source_system",
        y="value",
        color="metric",
        barmode="group",
        title="Integration Health by Source System",
        color_discrete_map={
            "healthy_rate": PALETTE["green"],
            "degraded_rate": PALETTE["amber"],
            "failed_rate": PALETTE["red"],
        },
    )
    fig.update_xaxes(title="Source System")
    fig.update_yaxes(title="Rate")
    return _base_layout(fig, "Integration Health", height=370)


def plot_anomalies(df: pd.DataFrame, anomalies_df: pd.DataFrame) -> go.Figure:
    """Plot anomaly counts over time by anomaly type."""
    if anomalies_df.empty:
        return _base_layout(go.Figure(), "Anomaly Detection")

    anomalies = anomalies_df.copy()
    anomalies["date"] = pd.to_datetime(anomalies["timestamp"]).dt.floor("D")
    grouped = anomalies.groupby(["date", "anomaly_type"], as_index=False).agg(events=("timestamp", "count"))

    fig = px.area(
        grouped,
        x="date",
        y="events",
        color="anomaly_type",
        title="Operational Anomalies Over Time",
    )
    fig.update_xaxes(title="Date")
    fig.update_yaxes(title="Anomaly Events")
    return _base_layout(fig, "Anomaly Detection", height=370)


def plot_esg_distribution(df: pd.DataFrame) -> go.Figure:
    """Plot ESG score distribution histogram."""
    if df.empty:
        return _base_layout(go.Figure(), "ESG Distribution")

    fig = px.histogram(
        df,
        x="esg_score",
        nbins=24,
        title="ESG Score Distribution",
        color_discrete_sequence=[PALETTE["teal"]],
    )
    fig.update_xaxes(title="ESG Score")
    fig.update_yaxes(title="Events")
    return _base_layout(fig, "ESG Distribution", height=340)


def plot_workflow_replay(df: pd.DataFrame) -> go.Figure:
    """Plot cumulative daily operational event flow for replay context."""
    if df.empty:
        return _base_layout(go.Figure(), "Workflow Replay")

    replay = df.copy().sort_values("timestamp")
    replay["date"] = pd.to_datetime(replay["timestamp"]).dt.floor("D")
    daily = replay.groupby(["date", "workflow_stage"], as_index=False).agg(events=("timestamp", "count"))

    fig = px.area(
        daily,
        x="date",
        y="events",
        color="workflow_stage",
        title="Workflow Replay by Stage",
    )
    fig.update_xaxes(title="Date")
    fig.update_yaxes(title="Events")
    return _base_layout(fig, "Workflow Replay", height=380)


def plot_stage_bottlenecks(df: pd.DataFrame) -> go.Figure:
    """Plot bottleneck severity by workflow stage."""
    if df.empty or "workflow_stage" not in df.columns:
        return _base_layout(go.Figure(), "Workflow Bottlenecks")

    columns = {"workflow_stage", "severity", "avg_duration_hours"}
    if columns.issubset(set(df.columns)):
        bottlenecks = df.copy()
    else:
        bottlenecks = (
            df.groupby("workflow_stage", as_index=False)
            .agg(avg_duration_hours=("latency_ms", "mean"))
            .assign(severity=lambda frame: frame["avg_duration_hours"] / frame["avg_duration_hours"].max())
        )

    fig = px.bar(
        bottlenecks,
        x="workflow_stage",
        y="severity",
        color="avg_duration_hours" if "avg_duration_hours" in bottlenecks.columns else "severity",
        title="Workflow Bottleneck Severity",
        color_continuous_scale=[PALETTE["green"], PALETTE["amber"], PALETTE["red"]],
    )
    fig.update_xaxes(title="Workflow Stage")
    fig.update_yaxes(title="Severity")
    return _base_layout(fig, "Workflow Bottlenecks", height=350)
