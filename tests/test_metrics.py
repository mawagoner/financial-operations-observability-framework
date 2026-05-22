"""Operational KPI metric tests."""

from __future__ import annotations

from finance_ops.analytics.metrics import summarize_by_workflow_stage, summarize_kpis, summarize_operational_latency
from finance_ops.generator import generate_sample_finance_operations_data


def test_kpi_summary_contains_expected_fields() -> None:
    events = generate_sample_finance_operations_data(num_customers=120, num_loans=260, days=50, seed=3)
    kpis = summarize_kpis(events)
    expected = {
        "total_events",
        "unique_entities",
        "unique_customers",
        "payment_completion_rate",
        "workflow_completion_rate",
        "avg_workflow_completion_hours",
        "average_risk_score",
        "average_esg_score",
        "avg_latency_ms",
        "integration_failure_count",
        "anomaly_count",
        "delayed_payment_percentage",
    }
    assert expected.issubset(set(kpis.keys()))


def test_stage_and_latency_summaries_not_empty() -> None:
    events = generate_sample_finance_operations_data(num_customers=120, num_loans=260, days=50, seed=13)
    stage_summary = summarize_by_workflow_stage(events)
    latency_summary = summarize_operational_latency(events)
    assert not stage_summary.empty
    assert not latency_summary.empty
