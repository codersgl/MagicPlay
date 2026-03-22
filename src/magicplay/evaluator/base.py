"""
Base classes for quality evaluation in MagicPlay.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class QualityLevel(Enum):
    """Quality level classification."""

    EXCELLENT = "excellent"  # A级：可直接使用，高质量
    GOOD = "good"  # B级：可接受，质量良好
    ACCEPTABLE = "acceptable"  # C级：勉强可用，可能需要优化
    POOR = "poor"  # D级：质量差，建议重生成
    UNUSABLE = "unusable"  # E级：无法使用，必须重生成


@dataclass
class EvaluationResult:
    """Result of a quality evaluation."""

    score: float  # 0-100 score
    quality_level: QualityLevel
    metrics: Dict[str, float]  # Detailed metrics
    issues: List[str]  # List of detected issues
    recommendations: List[str]  # Recommendations for improvement
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata (image hash, etc.)

    def __post_init__(self):
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_acceptable(self) -> bool:
        """Check if the quality is acceptable for use."""
        return self.quality_level in [
            QualityLevel.EXCELLENT,
            QualityLevel.GOOD,
            QualityLevel.ACCEPTABLE,
        ]

    @property
    def needs_regeneration(self) -> bool:
        """Check if regeneration is recommended."""
        return self.quality_level in [QualityLevel.POOR, QualityLevel.UNUSABLE]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "score": self.score,
            "quality_level": self.quality_level.value,
            "metrics": self.metrics,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "metadata": self.metadata or {},
            "is_acceptable": self.is_acceptable,
            "needs_regeneration": self.needs_regeneration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationResult":
        """Create from dictionary."""
        return cls(
            score=data["score"],
            quality_level=QualityLevel(data["quality_level"]),
            metrics=data["metrics"],
            issues=data["issues"],
            recommendations=data["recommendations"],
            metadata=data.get("metadata", {}),
        )


class BaseEvaluator(ABC):
    """Base class for all quality evaluators."""

    def __init__(self, name: str, version: str = "1.0"):
        self.name = name
        self.version = version
        self.thresholds = {
            QualityLevel.EXCELLENT: 85.0,
            QualityLevel.GOOD: 70.0,
            QualityLevel.ACCEPTABLE: 55.0,
            QualityLevel.POOR: 40.0,
            # Below 40 is UNUSABLE
        }

    @abstractmethod
    def evaluate(self, input_data: Union[str, Path, Any], **kwargs) -> EvaluationResult:
        """
        Evaluate the quality of input data.

        Args:
            input_data: Path to file or data to evaluate
            **kwargs: Additional evaluation parameters

        Returns:
            EvaluationResult with quality assessment
        """
        pass

    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level based on score."""
        if score >= self.thresholds[QualityLevel.EXCELLENT]:
            return QualityLevel.EXCELLENT
        elif score >= self.thresholds[QualityLevel.GOOD]:
            return QualityLevel.GOOD
        elif score >= self.thresholds[QualityLevel.ACCEPTABLE]:
            return QualityLevel.ACCEPTABLE
        elif score >= self.thresholds[QualityLevel.POOR]:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNUSABLE

    def _calculate_score(
        self, metrics: Dict[str, float], weights: Dict[str, float]
    ) -> float:
        """
        Calculate overall score from weighted metrics.

        Args:
            metrics: Dictionary of metric names to values (0-1 or 0-100)
            weights: Dictionary of metric weights (should sum to 1.0)

        Returns:
            Weighted score (0-100)
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for metric_name, weight in weights.items():
            if metric_name in metrics:
                # Ensure metric is in 0-100 range
                metric_value = metrics[metric_name]
                if 0 <= metric_value <= 1:  # Likely 0-1 range
                    metric_value *= 100
                weighted_sum += metric_value * weight
                total_weight += weight

        # Normalize by total weight used
        if total_weight > 0:
            return weighted_sum / total_weight
        return 0.0

    def validate_input(
        self, input_data: Union[str, Path, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input data before evaluation.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if isinstance(input_data, (str, Path)):
            path = Path(input_data)
            if not path.exists():
                return False, f"File does not exist: {path}"
            if not path.is_file():
                return False, f"Path is not a file: {path}"
        return True, None

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"
