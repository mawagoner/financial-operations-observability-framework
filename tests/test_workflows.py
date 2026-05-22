"""Workflow replay and transition analytics tests."""

from __future__ import annotations

from finance_ops.analytics.workflows import (
    calculate_stage_durations,
    detect_bottlenecks,
    reconstruct_workflow_timeline,
    summarize_workflow_transitions,
)
from finance_ops.generator import generate_sample_finance_operations_data


def test_reconstruct_workflow_timeline_sorted() -> None:
    events = generate_sample_finance_operations_data(num_customers=120, num_loans=220, days=50, seed=17)
    entity_id = str(events["entity_id"].iloc[0])
    timeline = reconstruct_workflow_timeline(events, entity_id)
    assert not timeline.empty
    assert timeline["timestamp"].is_monotonic_increasing


def test_transition_and_bottleneck_outputs() -> None:
    events = generate_sample_finance_operations_data(num_customers=120, num_loans=220, days=50, seed=19)
    transitions = summarize_workflow_transitions(events)
    durations = calculate_stage_durations(events)
    bottlenecks = detect_bottlenecks(events)

    assert {"from_stage", "to_stage", "transition_count", "share"}.issubset(set(transitions.columns))
    assert {"workflow_stage", "avg_duration_hours", "p90_duration_hours"}.issubset(set(durations.columns))
    assert {"workflow_stage", "severity", "explanation"}.issubset(set(bottlenecks.columns))
