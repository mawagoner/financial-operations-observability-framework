"""Operational anomaly detection tests."""

from __future__ import annotations

import pandas as pd

from finance_ops.analytics.anomalies import detect_anomalies
from finance_ops.generator import generate_sample_finance_operations_data


def test_detect_anomalies_returns_dataframe() -> None:
    events = generate_sample_finance_operations_data(num_customers=120, num_loans=280, days=60, seed=23)
    anomalies = detect_anomalies(events)
    assert isinstance(anomalies, pd.DataFrame)


def test_anomaly_dataframe_has_expected_columns() -> None:
    events = generate_sample_finance_operations_data(num_customers=120, num_loans=280, days=60, seed=29)
    anomalies = detect_anomalies(events)
    expected_columns = {
        "timestamp",
        "anomaly_type",
        "severity",
        "affected_entity",
        "explanation",
        "source_system",
    }
    assert expected_columns.issubset(set(anomalies.columns))
