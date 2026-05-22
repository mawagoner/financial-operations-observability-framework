"""Schema and sample generation tests."""

from __future__ import annotations

from finance_ops.generator import generate_sample_finance_operations_data
from finance_ops.schema import get_required_columns, validate_event_dataframe


def test_generated_events_have_required_columns() -> None:
    events = generate_sample_finance_operations_data(num_customers=120, num_loans=240, days=45, seed=7)
    required = set(get_required_columns())
    assert required.issubset(set(events.columns))


def test_generated_events_validate() -> None:
    events = generate_sample_finance_operations_data(num_customers=120, num_loans=240, days=45, seed=11)
    is_valid, errors = validate_event_dataframe(events)
    assert is_valid, f"Validation errors: {errors}"
