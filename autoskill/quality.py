from __future__ import annotations

from autoskill.reliability_score import (
    compute_reliability_components,
    compute_reliability_score_value,
    score_reliability_formula,
)


def score_reliability(*args, **kwargs):
    return score_reliability_formula(*args, **kwargs)


__all__ = [
    "compute_reliability_components",
    "compute_reliability_score_value",
    "score_reliability",
]
