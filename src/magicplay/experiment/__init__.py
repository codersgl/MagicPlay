"""
Experiment Management Framework for MagicPlay.

Provides tools for running A/B tests, tracking different generation configurations,
and optimizing quality/cost trade-offs.
"""
from .tracker import ExperimentTracker, ExperimentConfig, ExperimentResult, ExperimentStatus

__all__ = ["ExperimentTracker", "ExperimentConfig", "ExperimentResult", "ExperimentStatus"]