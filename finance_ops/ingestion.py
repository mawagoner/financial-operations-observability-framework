"""Ingestion and normalization entrypoints for heterogeneous finance ops data.

The goal of this module is to normalize data from different operational systems
that all describe overlapping business events in different dialects.

Today, this prototype supports:
- generated sample data
- CSV files and uploaded CSV-like buffers

The architecture is intentionally adapter-oriented so future connectors can map
from systems such as Salesforce, HubSpot, loan-servicing APIs, Plaid-like
account links, payment processors, ESG data vendors, investor-reporting feeds,
internal operational logs, and webhook streams.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .generator import generate_sample_finance_operations_data
from .schema import normalize_event_dataframe


def detect_input_format(file_name: str) -> str:
    """Infer input format from source label or file extension."""
    lowered = str(file_name).strip().lower()
    if lowered in {"sample", "generated", "generated sample data"}:
        return "sample"

    suffix = Path(lowered).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".json":
        return "json"
    if suffix in {".log", ".txt"}:
        return "log"
    return "unknown"


def _source_name(source: Any) -> str:
    if source is None:
        return "generated"
    if isinstance(source, str):
        return source
    if isinstance(source, pd.DataFrame):
        return "dataframe_input"
    if hasattr(source, "name"):
        return str(source.name)
    return "unknown_source"


def _standardize_external_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Map common operational aliases toward canonical schema fields.

    This lightweight mapping helps demonstrate heterogeneous system ingestion by
    translating popular field aliases without requiring heavyweight adapters.
    """
    aliases = {
        "event_time": "timestamp",
        "created_at": "timestamp",
        "system": "source_system",
        "source": "source_system",
        "record_type": "entity_type",
        "object_type": "entity_type",
        "record_id": "entity_id",
        "id": "entity_id",
        "client_id": "customer_id",
        "account_id": "customer_id",
        "stage": "workflow_stage",
        "status": "workflow_status",
        "type": "event_type",
        "amount": "transaction_amount",
        "payment_state": "payment_status",
        "score_risk": "risk_score",
        "score_esg": "esg_score",
        "team": "assigned_team",
        "latency": "latency_ms",
        "integration_health": "integration_status",
        "is_anomaly": "anomaly_flag",
        "comment": "notes",
    }
    rename_map = {column: aliases[column] for column in frame.columns if column in aliases}
    return frame.rename(columns=rename_map)


def load_csv(file: Any) -> pd.DataFrame:
    """Load and normalize events from CSV source."""
    raw = pd.read_csv(file)
    raw = _standardize_external_columns(raw)
    return normalize_event_dataframe(raw)


def load_sample_data(config: dict[str, Any] | None = None) -> pd.DataFrame:
    """Load normalized generated finance operations events."""
    config = config or {}
    return generate_sample_finance_operations_data(
        num_customers=int(config.get("num_customers", 500)),
        num_loans=int(config.get("num_loans", 1000)),
        days=int(config.get("days", 90)),
        seed=int(config.get("seed", 42)),
    )


def ingest_events(source: Any, config: dict[str, Any] | None = None) -> pd.DataFrame:
    """Unified ingestion function for sample, CSV, and in-memory sources."""
    config = config or {}

    if source is None:
        return load_sample_data(config)

    if isinstance(source, pd.DataFrame):
        source_frame = _standardize_external_columns(source.copy())
        return normalize_event_dataframe(source_frame)

    if hasattr(source, "read"):
        return load_csv(source)

    source_name = _source_name(source)
    source_format = detect_input_format(source_name)

    if source_format == "sample":
        return load_sample_data(config)
    if source_format == "csv":
        return load_csv(source)

    raise ValueError(
        "Unsupported input source format. Supported formats: sample/generated and CSV. "
        f"Received source '{source_name}'."
    )
