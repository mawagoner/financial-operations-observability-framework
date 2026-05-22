"""Utility helpers shared by finance operations framework modules."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def median_absolute_deviation(values: pd.Series | np.ndarray) -> float:
    """Return robust spread estimate (MAD) for a numeric sequence."""
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return 0.0
    median = float(np.median(array))
    return float(np.median(np.abs(array - median)))


def safe_ratio(numerator: float, denominator: float) -> float:
    """Return numerator/denominator with zero-denominator protection."""
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def normalize_severity(value: float, baseline: float, floor: float = 0.1) -> float:
    """Scale anomaly intensity to a bounded severity score (0-1)."""
    magnitude = abs(float(value))
    baseline = max(abs(float(baseline)), floor)
    score = magnitude / baseline
    return float(np.clip(score, 0.0, 1.0))


def contiguous_periods(
    timestamps: pd.Series,
    mask: pd.Series,
    period_type: str,
) -> pd.DataFrame:
    """Convert boolean masks into contiguous start/end period tables."""
    if timestamps.empty:
        return pd.DataFrame(columns=["period_type", "start", "end", "points"])

    times = timestamps.reset_index(drop=True)
    flags = mask.fillna(False).reset_index(drop=True)
    records: list[dict[str, Any]] = []

    start_idx: int | None = None
    for idx, is_active in enumerate(flags.to_list()):
        if is_active and start_idx is None:
            start_idx = idx

        at_last = idx == len(flags) - 1
        if start_idx is not None and (not is_active or at_last):
            end_idx = idx if is_active and at_last else idx - 1
            records.append(
                {
                    "period_type": period_type,
                    "start": times.iloc[start_idx],
                    "end": times.iloc[end_idx],
                    "points": int(end_idx - start_idx + 1),
                }
            )
            start_idx = None

    return pd.DataFrame(records)
