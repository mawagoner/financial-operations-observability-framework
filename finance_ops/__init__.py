"""Financial operations observability and integration analytics framework."""

from .generator import generate_sample_finance_operations_data
from .ingestion import detect_input_format, ingest_events, load_csv, load_sample_data
from .schema import (
    CANONICAL_COLUMNS,
    get_optional_columns,
    get_required_columns,
    normalize_event_dataframe,
    validate_event_dataframe,
)

__all__ = [
    "CANONICAL_COLUMNS",
    "detect_input_format",
    "generate_sample_finance_operations_data",
    "get_optional_columns",
    "get_required_columns",
    "ingest_events",
    "load_csv",
    "load_sample_data",
    "normalize_event_dataframe",
    "validate_event_dataframe",
]

__version__ = "1.0.0"
