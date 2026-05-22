"""Streamlit demo app for financial operations observability framework."""

from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import streamlit as st

from finance_ops import __version__, ingest_events
from finance_ops.analytics import (
    analyze_esg_by_region,
    analyze_payment_delays,
    build_audit_event_summary,
    build_payment_timeline,
    calculate_stage_durations,
    compare_regions_by_risk,
    detect_anomalies,
    detect_bottlenecks,
    detect_failed_integrations,
    detect_high_risk_clusters,
    detect_synchronization_gaps,
    summarize_by_region,
    summarize_by_team,
    summarize_by_workflow_stage,
    summarize_collections_escalations,
    summarize_delinquency,
    summarize_impact_scores,
    summarize_integration_health,
    summarize_investor_reporting,
    summarize_kpis,
    summarize_operational_exports,
    summarize_operational_latency,
    summarize_payment_completion,
    summarize_payment_metrics,
    summarize_workflow_transitions,
    track_esg_changes_over_time,
    track_risk_changes_over_time,
)
from finance_ops.replay import calculate_workflow_state, get_system_snapshot, reconstruct_entity_timeline, replay_operational_day
from finance_ops.visualization import (
    plot_anomalies,
    plot_esg_distribution,
    plot_integration_health,
    plot_latency_over_time,
    plot_operational_timeline,
    plot_payment_flow,
    plot_risk_distribution,
    plot_stage_bottlenecks,
    plot_workflow_pipeline,
    plot_workflow_replay,
)


st.set_page_config(page_title="Financial Operations Observability Framework", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp {
  font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
}
.stApp {
  background: radial-gradient(circle at 20% 0%, #eef4f8 0%, #f9fbfd 40%, #ffffff 100%);
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h1,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h2,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h3,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h4,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h5,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h6,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] p,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] li,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] label,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"],
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stHeadingWithActionElements"] {
  color: #102a43 !important;
  opacity: 1 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] button[data-baseweb="tab"] {
  color: #5f7387 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] button[data-baseweb="tab"][aria-selected="true"] {
  color: #15384f !important;
  font-weight: 600;
}
div[data-testid="stMetric"] {
  background: linear-gradient(150deg, #f8fbfd 0%, #eef4f8 100%);
  border: 1px solid #dbe5ec;
  border-radius: 12px;
  padding: 0.6rem 0.7rem;
}
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricValue"] {
  color: #163248 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def _load_generated(config: dict[str, int]) -> pd.DataFrame:
    return ingest_events("sample", config=config)


@st.cache_data(show_spinner=False)
def _load_uploaded(file_bytes: bytes) -> pd.DataFrame:
    return ingest_events(io.BytesIO(file_bytes))


def _plot(fig: object) -> None:
    st.plotly_chart(fig, use_container_width=True, theme=None)


def _render_sidebar() -> tuple[pd.DataFrame, float, float, float, pd.Timestamp]:
    st.sidebar.title("Observability Controls")

    source_mode = st.sidebar.radio("Data source", options=["Generated sample data", "Upload CSV data"], index=0)

    if source_mode == "Generated sample data":
        config = {
            "num_customers": int(st.sidebar.slider("Customers", 100, 2000, 500, step=50)),
            "num_loans": int(st.sidebar.slider("Loans", 200, 4000, 1000, step=100)),
            "days": int(st.sidebar.slider("Days", 30, 365, 90, step=15)),
            "seed": int(st.sidebar.number_input("Random seed", min_value=1, max_value=99999, value=42)),
        }
        events = _load_generated(config)
    else:
        uploaded = st.sidebar.file_uploader("Upload event CSV", type=["csv"])
        if uploaded is None:
            st.warning("Upload a CSV file or switch to generated data.")
            st.stop()
        events = _load_uploaded(uploaded.getvalue())

    min_date = events["timestamp"].min().date()
    max_date = events["timestamp"].max().date()

    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates  # type: ignore[assignment]

    region_options = sorted(events["region"].dropna().unique().tolist())
    selected_regions = st.sidebar.multiselect("Regions", options=region_options, default=region_options)

    stage_options = sorted(events["workflow_stage"].dropna().unique().tolist())
    selected_stages = st.sidebar.multiselect("Workflow stages", options=stage_options, default=stage_options)

    team_options = sorted(events["assigned_team"].dropna().unique().tolist())
    selected_teams = st.sidebar.multiselect("Teams", options=team_options, default=team_options)

    filtered = events[
        (events["region"].isin(selected_regions))
        & (events["workflow_stage"].isin(selected_stages))
        & (events["assigned_team"].isin(selected_teams))
        & (events["timestamp"].dt.date >= start_date)
        & (events["timestamp"].dt.date <= end_date)
    ].copy()

    if filtered.empty:
        st.warning("No data remains after filters. Adjust sidebar controls.")
        st.stop()

    anomaly_latency_quantile = float(
        st.sidebar.slider("Anomaly latency quantile", min_value=0.90, max_value=0.999, value=0.98, step=0.005)
    )
    risk_jump_threshold = float(st.sidebar.slider("Risk jump threshold", min_value=8, max_value=40, value=18, step=1))
    stall_hours = float(st.sidebar.slider("Workflow stall threshold (hours)", min_value=24, max_value=240, value=72, step=12))

    replay_timestamps = filtered["timestamp"].sort_values().unique()
    replay_idx = st.sidebar.slider("Replay timestamp step", 0, len(replay_timestamps) - 1, len(replay_timestamps) - 1)
    replay_timestamp = pd.Timestamp(replay_timestamps[int(replay_idx)])

    return filtered, anomaly_latency_quantile, risk_jump_threshold, stall_hours, replay_timestamp


def render() -> None:
    st.title("Financial Operations Observability & Integration Analytics Framework")
    st.caption(f"v{__version__} · Portfolio Prototype")
    st.info(
        "Different operational systems speak different dialects. "
        "This framework demonstrates how they can be normalized into a unified "
        "analytics and observability layer."
    )

    events, latency_q, risk_jump, stall_hours, replay_timestamp = _render_sidebar()

    anomalies_df = detect_anomalies(
        events,
        latency_quantile=latency_q,
        risk_jump_threshold=risk_jump,
        stall_hours=stall_hours,
    )

    kpis = summarize_kpis(events)
    stage_summary = summarize_by_workflow_stage(events)
    region_summary = summarize_by_region(events)
    latency_summary = summarize_operational_latency(events)

    workflow_transitions = summarize_workflow_transitions(events)
    stage_durations = calculate_stage_durations(events)
    bottlenecks = detect_bottlenecks(events)

    payment_summary = summarize_payment_metrics(events)
    payment_completion = summarize_payment_completion(events)
    delinquency = summarize_delinquency(events)
    payment_delays = analyze_payment_delays(events)
    collections_summary = summarize_collections_escalations(events)

    risk_region = compare_regions_by_risk(events)
    risk_clusters = detect_high_risk_clusters(events)
    risk_trend = track_risk_changes_over_time(events)

    esg_impact = summarize_impact_scores(events)
    esg_region = analyze_esg_by_region(events)
    esg_trend = track_esg_changes_over_time(events)

    integration_health = summarize_integration_health(events)
    integration_failures = detect_failed_integrations(events)
    sync_gaps = detect_synchronization_gaps(events)

    investor_reporting = summarize_investor_reporting(events)
    export_summary = summarize_operational_exports(events)
    audit_summary = build_audit_event_summary(events)

    snapshot = get_system_snapshot(events, replay_timestamp)
    daily_replay = replay_operational_day(events, replay_timestamp)
    workflow_state = calculate_workflow_state(snapshot if not snapshot.empty else events)

    tabs = st.tabs(
        [
            "Overview",
            "Data Sources",
            "Workflow Pipeline",
            "Operational Replay",
            "Payment Analytics",
            "Risk Analytics",
            "ESG Metrics",
            "Integration Health",
            "Anomaly Detection",
            "Operational Latency",
            "Workflow Bottlenecks",
            "Entity Timeline Replay",
            "About This Framework",
        ]
    )

    with tabs[0]:
        cols = st.columns(6)
        cols[0].metric("Events", f"{int(kpis['total_events']):,}")
        cols[1].metric("Entities", f"{int(kpis['unique_entities']):,}")
        cols[2].metric("Payment Completion", f"{kpis['payment_completion_rate'] * 100:.1f}%")
        cols[3].metric("Workflow Completion", f"{kpis['workflow_completion_rate'] * 100:.1f}%")
        cols[4].metric("Avg Latency", f"{kpis['avg_latency_ms']:.0f} ms")
        cols[5].metric("Anomaly Events", f"{int(kpis['anomaly_count']):,}")

        _plot(plot_operational_timeline(events))
        st.caption(
            "Operational observability lens: this timeline merges heterogeneous system events "
            "after canonical normalization."
        )

    with tabs[1]:
        source_breakdown = events.groupby("source_system", as_index=False).agg(events=("timestamp", "count"))
        entity_breakdown = events.groupby("entity_type", as_index=False).agg(events=("timestamp", "count"))

        left, right = st.columns(2)
        left.subheader("Source Systems")
        left.dataframe(source_breakdown.sort_values("events", ascending=False), use_container_width=True, hide_index=True)
        right.subheader("Entity Types")
        right.dataframe(entity_breakdown.sort_values("events", ascending=False), use_container_width=True, hide_index=True)

        st.subheader("Regional Operations Summary")
        st.dataframe(region_summary, use_container_width=True, hide_index=True)
        st.subheader("Team Operations Summary")
        st.dataframe(summarize_by_team(events), use_container_width=True, hide_index=True)

    with tabs[2]:
        _plot(plot_workflow_pipeline(events))
        left, right = st.columns(2)
        left.subheader("Stage Summary")
        left.dataframe(stage_summary, use_container_width=True, hide_index=True)
        right.subheader("Top Stage Transitions")
        right.dataframe(workflow_transitions.head(20), use_container_width=True, hide_index=True)

    with tabs[3]:
        st.write(f"Replay timestamp: `{replay_timestamp}`")
        replay_base = events[events["timestamp"] <= replay_timestamp].copy()
        _plot(plot_workflow_replay(replay_base))

        c1, c2 = st.columns(2)
        c1.subheader("Workflow State Snapshot")
        c1.dataframe(workflow_state, use_container_width=True, hide_index=True)
        c2.subheader("Operational Day Replay")
        c2.dataframe(daily_replay.head(60), use_container_width=True, hide_index=True)

    with tabs[4]:
        cards = st.columns(4)
        cards[0].metric("Payment Events", f"{int(payment_summary['payment_events']):,}")
        cards[1].metric("Completed", f"{payment_completion['completed_rate'] * 100:.1f}%")
        cards[2].metric("Delayed", f"{payment_completion['delayed_rate'] * 100:.1f}%")
        cards[3].metric("Failed", f"{payment_completion['failed_rate'] * 100:.1f}%")

        _plot(plot_payment_flow(events))
        st.subheader("Payment Timeline")
        st.dataframe(build_payment_timeline(events), use_container_width=True, hide_index=True)
        st.subheader("Delinquency")
        st.dataframe(delinquency.head(30), use_container_width=True, hide_index=True)
        st.subheader("Payment Delay Analysis")
        st.dataframe(payment_delays.head(30), use_container_width=True, hide_index=True)
        st.subheader("Collections Escalations")
        st.dataframe(collections_summary.head(30), use_container_width=True, hide_index=True)

    with tabs[5]:
        _plot(plot_risk_distribution(events))
        trend_fig = px.line(risk_trend, x="date", y=["avg_risk_score", "p90_risk_score"], title="Risk Trend Over Time")
        trend_fig.update_layout(
            template="plotly_white",
            height=320,
            font={"color": "#1f2933"},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        _plot(trend_fig)
        left, right = st.columns(2)
        left.subheader("Regional Risk Comparison")
        left.dataframe(risk_region, use_container_width=True, hide_index=True)
        right.subheader("High-Risk Clusters")
        right.dataframe(risk_clusters.head(25), use_container_width=True, hide_index=True)

    with tabs[6]:
        cards = st.columns(4)
        cards[0].metric("Avg ESG", f"{esg_impact['average_esg_score']:.1f}")
        cards[1].metric("High Impact", f"{esg_impact['high_impact_share'] * 100:.1f}%")
        cards[2].metric("Low Impact", f"{esg_impact['low_impact_share'] * 100:.1f}%")
        cards[3].metric("ESG Updates", f"{int(esg_impact['esg_update_events']):,}")

        _plot(plot_esg_distribution(events))
        esg_trend_fig = px.line(esg_trend, x="date", y="avg_esg_score", title="Average ESG Over Time")
        esg_trend_fig.update_layout(
            template="plotly_white",
            height=320,
            font={"color": "#1f2933"},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        _plot(esg_trend_fig)
        st.dataframe(esg_region, use_container_width=True, hide_index=True)

    with tabs[7]:
        _plot(plot_integration_health(events))
        st.subheader("Integration Health Summary")
        st.dataframe(integration_health, use_container_width=True, hide_index=True)
        st.subheader("Failed or Degraded Integration Events")
        st.dataframe(integration_failures.head(80), use_container_width=True, hide_index=True)
        st.subheader("Cross-System Synchronization Gaps")
        st.dataframe(sync_gaps.head(60), use_container_width=True, hide_index=True)

    with tabs[8]:
        _plot(plot_anomalies(events, anomalies_df))
        st.dataframe(anomalies_df.head(120), use_container_width=True, hide_index=True)

    with tabs[9]:
        _plot(plot_latency_over_time(events))
        st.dataframe(latency_summary.head(100), use_container_width=True, hide_index=True)

    with tabs[10]:
        _plot(plot_stage_bottlenecks(bottlenecks))
        left, right = st.columns(2)
        left.subheader("Stage Durations")
        left.dataframe(stage_durations, use_container_width=True, hide_index=True)
        right.subheader("Detected Bottlenecks")
        right.dataframe(bottlenecks, use_container_width=True, hide_index=True)

    with tabs[11]:
        entities = sorted(events["entity_id"].unique().tolist())
        selected_entity = st.selectbox("Select entity for replay", entities, index=min(10, len(entities) - 1))
        entity_timeline = reconstruct_entity_timeline(events, selected_entity)

        st.dataframe(entity_timeline.head(120), use_container_width=True, hide_index=True)
        if not entity_timeline.empty:
            entity_plot = px.scatter(
                entity_timeline,
                x="timestamp",
                y="workflow_stage",
                color="workflow_status",
                hover_data=["event_type", "source_system", "latency_ms"],
                title=f"Entity Timeline Replay: {selected_entity}",
            )
            entity_plot.update_layout(
                template="plotly_white",
                height=360,
                font={"color": "#1f2933"},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            _plot(entity_plot)

    with tabs[12]:
        st.markdown(
            """
This prototype models how operations teams can observe and analyze events across
loan servicing exports, CRM records, payment processors, underwriting decisions,
ESG feeds, investor reporting, and integration infrastructure.

Core thesis:

**Different operational systems speak different dialects. This framework normalizes
them into a unified operational analytics and observability layer.**

The architecture is intentionally modular so teams can extend ingestion adapters,
replay workflows, and analytics modules without rebuilding the full stack.
"""
        )
        st.subheader("Reporting Snapshots")
        st.dataframe(investor_reporting.head(40), use_container_width=True, hide_index=True)
        st.subheader("Operational Export Summary")
        st.dataframe(export_summary.head(40), use_container_width=True, hide_index=True)
        st.subheader("Audit Event Summary")
        st.dataframe(audit_summary.head(40), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render()
