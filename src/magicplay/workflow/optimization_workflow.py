"""
Optimization workflow for finding optimal generation configurations.

This module provides the OptimizationWorkflow class which experiments with
different generation configurations to find the optimal balance between
quality and cost.
"""

from typing import Dict, List, Optional, Tuple

from loguru import logger

from ..evaluator.base import EvaluationResult, QualityLevel
from ..experiment.tracker import ExperimentConfig, ExperimentResult, ExperimentTracker
from ..resource_registry.registry import (
    ResourceRecord,
    ResourceRegistry,
    ResourceState,
    ResourceType,
)


class OptimizationWorkflow:
    """
    Workflow for finding optimal generation configurations through experimentation.

    This workflow runs experiments with different generation configurations
    and evaluates their results to find the best configuration for given
    quality and cost constraints.
    """

    def __init__(
        self,
        target_quality: float = 80.0,
        max_cost: float = 5.0,
        strategy: str = "balanced",
        registry: Optional[ResourceRegistry] = None,
        tracker: Optional[ExperimentTracker] = None,
    ):
        """
        Initialize optimization workflow.

        Args:
            target_quality: Target quality score (0-100)
            max_cost: Maximum cost allowed for generation
            strategy: Optimization strategy ("quality_first", "balanced", "cost_optimized")
            registry: Resource registry for caching
            tracker: Experiment tracker for recording results
        """
        self.target_quality = target_quality
        self.max_cost = max_cost
        self.strategy = strategy.lower()
        self.registry = registry or ResourceRegistry()
        self.tracker = tracker or ExperimentTracker()
        self.logger = logger

        # Validate strategy
        valid_strategies = ["quality_first", "balanced", "cost_optimized"]
        if self.strategy not in valid_strategies:
            raise ValueError(f"Strategy must be one of {valid_strategies}")

    def find_optimal_configuration(
        self,
        prompt: str,
        candidate_configs: Optional[List[ExperimentConfig]] = None,
        max_iterations: int = 5,
    ) -> Optional[ExperimentConfig]:
        """
        Find optimal configuration through experimentation.

        Args:
            prompt: Prompt for generation
            candidate_configs: List of candidate configurations to test
            max_iterations: Maximum number of iterations to run

        Returns:
            Optimal configuration found, or None if no configuration meets requirements
        """
        self.logger.info(f"Starting optimization workflow for prompt: {prompt}")

        # Create default configurations if none provided
        if not candidate_configs:
            candidate_configs = self._create_default_configurations()

        best_config = None
        best_score = -float("inf")

        # Test each candidate configuration
        for config in candidate_configs:
            self.logger.info(f"Testing configuration: {config.name}")

            # Run experiment with this configuration
            resource, evaluation, cost = self._run_experiment(config, prompt)

            if resource and evaluation:
                # Calculate score based on strategy
                score = self._calculate_config_score(
                    quality=evaluation.score,
                    cost=cost,
                    meets_quality=evaluation.score >= self.target_quality,
                    meets_cost=cost <= self.max_cost,
                )

                # Record experiment result
                result = ExperimentResult(
                    experiment_id=config.config_id,
                    config=config,
                    resource_record=resource,
                    evaluation_result=evaluation,
                    total_cost=cost,
                    total_time=0.0,  # Would be measured in real implementation
                    attempts=1,
                    success=True,
                )

                if self.tracker:
                    self.tracker.record_result(config.config_id, result)

                # Update best configuration
                if score > best_score:
                    best_score = score
                    best_config = config

                self.logger.info(
                    f"Configuration {config.name}: quality={evaluation.score:.1f}, cost={cost:.2f}, score={score:.2f}"
                )

                # Early exit if we found a configuration that meets all requirements
                if evaluation.score >= self.target_quality and cost <= self.max_cost:
                    self.logger.info(f"Found optimal configuration: {config.name}")
                    break

        if best_config:
            self.logger.info(
                f"Selected configuration: {best_config.name} with score {best_score:.2f}"
            )
        else:
            self.logger.warning("No suitable configuration found")

        return best_config

    def _run_experiment(
        self,
        config: ExperimentConfig,
        prompt: str,
    ) -> Tuple[Optional[ResourceRecord], Optional[EvaluationResult], float]:
        """
        Run a single experiment with given configuration.

        This is a placeholder that should be implemented with actual generation
        logic. In a real implementation, this would call image/video generation
        services and evaluate the results.

        Args:
            config: Experiment configuration
            prompt: Generation prompt

        Returns:
            Tuple of (resource_record, evaluation_result, cost)
        """
        # This is a mock implementation
        # In practice, this would:
        # 1. Generate resource (image/video) using the configuration
        # 2. Evaluate quality
        # 3. Calculate cost

        self.logger.debug(f"Running experiment for config: {config.name}")

        # Mock generation parameters
        quality = config.parameters.get("quality", 75.0)
        cost = config.parameters.get("cost", 2.0)

        # Create mock resource
        resource = ResourceRecord(
            resource_id=f"exp-{config.name}-{hash(prompt) % 1000:04d}",
            resource_type=ResourceType.CHARACTER_IMAGE,
            metadata={
                "prompt": prompt,
                "config_name": config.name,
                "experiment": True,
                "tags": ["experiment", config.name],  # Store tags in metadata
            },
            quality_score=quality,
            generation_cost=cost,
            state=ResourceState.VALIDATED,
        )

        # Create mock evaluation
        evaluation = EvaluationResult(
            score=quality,
            quality_level=self._map_quality_level(quality),
            metrics={
                "mock_metric_1": quality * 0.9,
                "mock_metric_2": quality * 0.8,
            },
            issues=[] if quality >= 70.0 else ["Low quality"],
            recommendations=["Increase steps"] if quality < 80.0 else [],
        )

        return resource, evaluation, cost

    def _calculate_config_score(
        self,
        quality: float,
        cost: float,
        meets_quality: bool,
        meets_cost: bool,
    ) -> float:
        """Calculate score for a configuration based on strategy."""
        if self.strategy == "quality_first":
            # Prioritize quality
            if not meets_quality:
                return -float("inf")
            return quality - (cost / 10.0)  # Small cost penalty

        elif self.strategy == "cost_optimized":
            # Prioritize cost
            if not meets_cost:
                return -float("inf")
            return (100.0 - cost * 10.0) + (quality / 10.0)  # Small quality bonus

        else:  # balanced
            # Balance quality and cost
            quality_score = quality / 100.0  # Normalize to 0-1
            cost_score = max(0, 1.0 - (cost / self.max_cost))  # Normalize to 0-1

            # Weighted combination (can be adjusted)
            return 0.7 * quality_score + 0.3 * cost_score

    def _create_default_configurations(self) -> List[ExperimentConfig]:
        """Create default experiment configurations."""
        return [
            ExperimentConfig(
                name="High Quality Config",
                description="High quality generation with more steps",
                parameters={
                    "model": "stable-diffusion-xl",
                    "steps": 100,
                    "cfg_scale": 9.0,
                    "quality": 95.0,
                    "cost": 8.0,
                },
                tags=["high_quality", "experiment"],
                min_quality_threshold=90.0,
                max_cost_limit=10.0,
            ),
            ExperimentConfig(
                name="Balanced Config",
                description="Balanced quality and cost",
                parameters={
                    "model": "stable-diffusion-xl",
                    "steps": 50,
                    "cfg_scale": 7.5,
                    "quality": 85.0,
                    "cost": 4.0,
                },
                tags=["balanced", "experiment"],
                min_quality_threshold=80.0,
                max_cost_limit=5.0,
            ),
            ExperimentConfig(
                name="Low Cost Config",
                description="Low cost generation with acceptable quality",
                parameters={
                    "model": "stable-diffusion",
                    "steps": 25,
                    "cfg_scale": 6.0,
                    "quality": 70.0,
                    "cost": 1.5,
                },
                tags=["low_cost", "experiment"],
                min_quality_threshold=60.0,
                max_cost_limit=2.0,
            ),
        ]

    def _map_quality_level(self, score: float) -> QualityLevel:
        """Map quality score to QualityLevel."""
        if score >= 85.0:
            return QualityLevel.EXCELLENT
        elif score >= 70.0:
            return QualityLevel.GOOD
        elif score >= 55.0:
            return QualityLevel.ACCEPTABLE
        elif score >= 40.0:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNUSABLE

    def get_optimization_summary(self) -> Dict:
        """Get summary of optimization results."""
        if not self.tracker:
            return {"error": "No experiment tracker available"}

        analysis = self.tracker.analyze_experiments()

        return {
            "target_quality": self.target_quality,
            "max_cost": self.max_cost,
            "strategy": self.strategy,
            "experiments_analyzed": analysis["total_experiments"],
            "configurations_tested": len(analysis["configurations"]),
            "best_configuration": analysis.get("best_by_quality", {}).get(
                "config_name"
            ),
            "most_cost_effective": analysis.get("best_by_cost", {}).get("config_name"),
        }
