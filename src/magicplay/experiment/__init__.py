"""
Experiment Management Framework for MagicPlay.

Provides tools for running A/B tests, tracking different generation configurations,
and optimizing quality/cost trade-offs.
"""

from .tracker import (
    ExperimentConfig,
    ExperimentResult,
    ExperimentStatus,
    ExperimentTracker,
)

__all__ = [
    "ExperimentTracker",
    "ExperimentConfig",
    "ExperimentResult",
    "ExperimentStatus",
]
