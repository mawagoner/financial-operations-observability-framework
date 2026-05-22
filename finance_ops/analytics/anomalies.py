"""Operational anomaly detection using lightweight statistical heuristics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..utils import normalize_severity


def detect_anomalies(
    df: pd.DataFrame,
    latency_quantile: float = 0.98,
    risk_jump_threshold: float = 18.0,
    esg_jump_threshold: float = 12.0,
    stall_hours: float = 72.0,
) -> pd.DataFrame:
    """Detect payment, integration, latency, workflow, risk, and ESG anomalies."""
    columns = ["timestamp", "anomaly_type", "severity", "affected_entity", "explanation", "source_system"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    working = df.sort_values(["entity_id", "timestamp"]).copy()
    records: list[dict[str, Any]] = []

    payment_events = working[working["payment_status"].isin(["delayed", "failed"])]
    for _, row in payment_events.iterrows():
        is_failed = row["payment_status"] == "failed"
        severity = 0.92 if is_failed else 0.68
        severity = min(1.0, severity + normalize_severity(row["transaction_amount"], baseline=9000.0) * 0.15)
        records.append(
            {
                "timestamp": row["timestamp"],
                "anomaly_type": "payment_anomaly",
                "severity": round(float(severity), 3),
                "affected_entity": row["entity_id"],
                "explanation": f"Payment marked {row['payment_status']}.",
                "source_system": row["source_system"],
            }
        )

    integration_failures = working[working["integration_status"].isin(["failed", "degraded"])]
    for _, row in integration_failures.iterrows():
        base = 0.86 if row["integration_status"] == "failed" else 0.55
        boost = normalize_severity(row["latency_ms"], baseline=1400.0) * 0.2
        records.append(
            {
                "timestamp": row["timestamp"],
                "anomaly_type": "integration_failure" if row["integration_status"] == "failed" else "integration_degradation",
                "severity": round(float(min(1.0, base + boost)), 3),
                "affected_entity": row["entity_id"],
                "explanation": f"Integration status is {row['integration_status']} with elevated latency.",
                "source_system": row["source_system"],
            }
        )

    for source_system, source_df in working.groupby("source_system", sort=False):
        threshold = float(source_df["latency_ms"].quantile(latency_quantile))
        threshold = max(200.0, threshold)
        spikes = source_df[source_df["latency_ms"] > threshold]
        for _, row in spikes.iterrows():
            records.append(
                {
                    "timestamp": row["timestamp"],
                    "anomaly_type": "latency_spike",
                    "severity": round(normalize_severity(row["latency_ms"], baseline=threshold), 3),
                    "affected_entity": row["entity_id"],
                    "explanation": f"Latency {row['latency_ms']:.1f}ms exceeded {latency_quantile:.0%} threshold ({threshold:.1f}ms).",
                    "source_system": source_system,
                }
            )

    for entity_id, entity_df in working.groupby("entity_id", sort=False):
        gaps = entity_df["timestamp"].diff().dt.total_seconds().div(3600.0)
        stalled = gaps > float(stall_hours)
        for idx in np.flatnonzero(stalled.fillna(False).to_numpy()):
            row = entity_df.iloc[idx]
            gap_hours = float(gaps.iloc[idx])
            records.append(
                {
                    "timestamp": row["timestamp"],
                    "anomaly_type": "workflow_stall",
                    "severity": round(normalize_severity(gap_hours, baseline=stall_hours), 3),
                    "affected_entity": entity_id,
                    "explanation": f"No events for {gap_hours:.1f} hours before this transition.",
                    "source_system": row["source_system"],
                }
            )

    risk_df = working.sort_values(["customer_id", "timestamp"]).copy()
    risk_df["risk_delta"] = risk_df.groupby("customer_id")["risk_score"].diff().abs()
    risk_jumps = risk_df[risk_df["risk_delta"] > float(risk_jump_threshold)]
    for _, row in risk_jumps.iterrows():
        records.append(
            {
                "timestamp": row["timestamp"],
                "anomaly_type": "risk_score_jump",
                "severity": round(normalize_severity(row["risk_delta"], baseline=risk_jump_threshold), 3),
                "affected_entity": row["customer_id"],
                "explanation": f"Risk score changed by {row['risk_delta']:.1f} points.",
                "source_system": row["source_system"],
            }
        )

    servicing_delay = working[
        (working["workflow_stage"].isin(["servicing", "collections"]))
        & (working["workflow_status"].isin(["delayed", "escalated"]))
        & (working["payment_status"].isin(["delayed", "failed"]))
    ]
    for _, row in servicing_delay.iterrows():
        records.append(
            {
                "timestamp": row["timestamp"],
                "anomaly_type": "servicing_delay",
                "severity": round(min(1.0, 0.55 + normalize_severity(row["latency_ms"], baseline=900.0) * 0.3), 3),
                "affected_entity": row["entity_id"],
                "explanation": "Delayed payment with servicing/collections escalation.",
                "source_system": row["source_system"],
            }
        )

    esg_df = working.sort_values(["customer_id", "timestamp"]).copy()
    esg_df["esg_delta"] = esg_df.groupby("customer_id")["esg_score"].diff().abs()
    inconsistent = esg_df[(esg_df["esg_delta"] > float(esg_jump_threshold)) | (esg_df["esg_score"] < 5.0)]
    for _, row in inconsistent.iterrows():
        delta_value = float(row["esg_delta"]) if pd.notna(row["esg_delta"]) else float(esg_jump_threshold)
        records.append(
            {
                "timestamp": row["timestamp"],
                "anomaly_type": "esg_inconsistency",
                "severity": round(normalize_severity(delta_value, baseline=esg_jump_threshold), 3),
                "affected_entity": row["customer_id"],
                "explanation": "ESG score shift exceeds expected reporting drift.",
                "source_system": row["source_system"],
            }
        )

    if not records:
        return pd.DataFrame(columns=columns)

    anomaly_df = pd.DataFrame(records).sort_values(["timestamp", "severity"], ascending=[True, False]).reset_index(drop=True)
    return anomaly_df[columns]
