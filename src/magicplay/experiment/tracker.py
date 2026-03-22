"""
Experiment Tracker for A/B testing and configuration optimization.

Features:
1. Track different generation configurations
2. Compare quality vs cost trade-offs
3. Run systematic experiments
4. Store results for analysis
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..evaluator.base import EvaluationResult
from ..resource_registry.registry import ResourceRecord


class ExperimentStatus(Enum):
    """Status of an experiment."""

    PLANNED = "planned"  # Experiment defined but not started
    RUNNING = "running"  # Experiment in progress
    COMPLETED = "completed"  # Experiment completed successfully
    FAILED = "failed"  # Experiment failed
    CANCELLED = "cancelled"  # Experiment cancelled


class ExperimentConfig:
    """Configuration for an experiment."""

    def __init__(
        self,
        name: str,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        min_quality_threshold: float = 60.0,
        max_cost_limit: Optional[float] = None,
        max_attempts: int = 3,
        model_variants: Optional[List[str]] = None,
        prompt_variants: Optional[List[str]] = None,
        generation_strategy: str = "balanced",
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        self.tags = tags or []
        self.min_quality_threshold = min_quality_threshold
        self.max_cost_limit = max_cost_limit
        self.max_attempts = max_attempts
        self.model_variants = model_variants or ["default"]
        self.prompt_variants = prompt_variants or ["default"]
        self.generation_strategy = generation_strategy
        self.created_at = datetime.now()
        self.config_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID for configuration."""
        config_str = json.dumps(
            {
                "name": self.name,
                "parameters": self.parameters,
                "model_variants": self.model_variants,
                "prompt_variants": self.prompt_variants,
                "generation_strategy": self.generation_strategy,
                "timestamp": self.created_at.isoformat(),
            },
            sort_keys=True,
        )
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "config_id": self.config_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "tags": self.tags,
            "min_quality_threshold": self.min_quality_threshold,
            "max_cost_limit": self.max_cost_limit,
            "max_attempts": self.max_attempts,
            "model_variants": self.model_variants,
            "prompt_variants": self.prompt_variants,
            "generation_strategy": self.generation_strategy,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentConfig":
        """Create from dictionary."""
        config = cls(
            name=data["name"],
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            tags=data.get("tags", []),
            min_quality_threshold=data.get("min_quality_threshold", 60.0),
            max_cost_limit=data.get("max_cost_limit"),
            max_attempts=data.get("max_attempts", 3),
            model_variants=data.get("model_variants", ["default"]),
            prompt_variants=data.get("prompt_variants", ["default"]),
            generation_strategy=data.get("generation_strategy", "balanced"),
        )
        config.config_id = data["config_id"]
        config.created_at = datetime.fromisoformat(data["created_at"])
        return config

    def create_variations(self) -> List["ExperimentConfig"]:
        """Create variations for A/B testing."""
        variations = []

        # Create variations for each model variant
        for model in self.model_variants:
            # Create variations for each prompt variant
            for prompt in self.prompt_variants:
                variant_name = f"{self.name}_model_{model}_prompt_{prompt}"
                variant_params = self.parameters.copy()
                variant_params.update(
                    {
                        "model_variant": model,
                        "prompt_variant": prompt,
                    }
                )

                variation = ExperimentConfig(
                    name=variant_name,
                    description=f"Variant of {self.name}: model={model}, prompt={prompt}",
                    parameters=variant_params,
                    tags=self.tags + [f"model:{model}", f"prompt:{prompt}"],
                    min_quality_threshold=self.min_quality_threshold,
                    max_cost_limit=self.max_cost_limit,
                    max_attempts=self.max_attempts,
                    model_variants=[model],
                    prompt_variants=[prompt],
                    generation_strategy=self.generation_strategy,
                )
                variations.append(variation)

        return variations

    def __str__(self) -> str:
        return f"{self.name} ({self.config_id})"


class ExperimentResult:
    """Result of an experiment run."""

    def __init__(
        self,
        experiment_id: str,
        config: ExperimentConfig,
        resource_record: Optional[ResourceRecord] = None,
        evaluation_result: Optional[EvaluationResult] = None,
        total_cost: float = 0.0,
        total_time: float = 0.0,
        attempts: int = 0,
        success: bool = False,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.experiment_id = experiment_id
        self.config = config
        self.resource_record = resource_record
        self.evaluation_result = evaluation_result
        self.total_cost = total_cost
        self.total_time = total_time
        self.attempts = attempts
        self.success = success
        self.error_message = error_message
        self.metadata = metadata or {}
        self.created_at = datetime.now()

    @property
    def quality_score(self) -> float:
        """Get quality score if available."""
        if self.evaluation_result:
            return self.evaluation_result.score
        return 0.0

    @property
    def cost_per_quality(self) -> float:
        """Calculate cost per quality point."""
        if self.quality_score > 0:
            return self.total_cost / self.quality_score
        return float("inf")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "config": self.config.to_dict(),
            "resource_record": (self.resource_record.to_dict() if self.resource_record else None),
            "evaluation_result": (self.evaluation_result.to_dict() if self.evaluation_result else None),
            "total_cost": self.total_cost,
            "total_time": self.total_time,
            "attempts": self.attempts,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "quality_score": self.quality_score,
            "cost_per_quality": self.cost_per_quality,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentResult":
        """Create from dictionary."""
        from ..evaluator.base import EvaluationResult as EvalResult

        # Parse evaluation result if present
        eval_result = None
        if data.get("evaluation_result"):
            eval_result = EvalResult.from_dict(data["evaluation_result"])

        # Parse resource record if present
        resource_record = None
        if data.get("resource_record"):
            from ..resource_registry.registry import ResourceRecord

            resource_record = ResourceRecord.from_dict(data["resource_record"])

        result = cls(
            experiment_id=data["experiment_id"],
            config=ExperimentConfig.from_dict(data["config"]),
            resource_record=resource_record,
            evaluation_result=eval_result,
            total_cost=data["total_cost"],
            total_time=data["total_time"],
            attempts=data["attempts"],
            success=data["success"],
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )
        result.created_at = datetime.fromisoformat(data["created_at"])
        return result

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return (
            f"{status} {self.config.name}: quality={self.quality_score:.1f}, "
            f"cost={self.total_cost:.3f}, time={self.total_time:.1f}s"
        )


class ExperimentTracker:
    """
    Tracks experiments and their results for systematic optimization.

    Features:
    - SQLite database for experiment storage
    - A/B testing support
    - Statistical analysis
    - Best configuration recommendation
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize tracker with SQLite database."""
        if db_path is None:
            # Default to project data directory
            from ..utils.paths import DataManager

            data_dir = DataManager.DATA_DIR
            db_path = data_dir / "experiment_tracker.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Experiments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    config_id TEXT NOT NULL,
                    config_name TEXT NOT NULL,
                    config_data TEXT NOT NULL,
                    status TEXT DEFAULT 'planned',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    tags TEXT
                )
            """)

            # Results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT NOT NULL,
                    run_number INTEGER DEFAULT 1,
                    result_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id)
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_experiment_status
                ON experiments(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_experiment_config
                ON experiments(config_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_experiment_tags
                ON experiments(tags)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_result_experiment
                ON experiment_results(experiment_id)
            """)

            conn.commit()

    def create_experiment(
        self,
        config: ExperimentConfig,
        status: ExperimentStatus = ExperimentStatus.PLANNED,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create a new experiment."""
        experiment_id = self._generate_experiment_id(config)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO experiments
                (experiment_id, config_id, config_name, config_data, status, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    experiment_id,
                    config.config_id,
                    config.name,
                    json.dumps(config.to_dict()),
                    status.value,
                    json.dumps(tags or []),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

        return experiment_id

    def _generate_experiment_id(self, config: ExperimentConfig) -> str:
        """Generate unique experiment ID."""
        unique_str = f"{config.config_id}_{datetime.now().timestamp()}"
        return hashlib.sha256(unique_str.encode()).hexdigest()[:16]

    def update_experiment_status(
        self,
        experiment_id: str,
        status: ExperimentStatus,
    ) -> bool:
        """Update experiment status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            update_fields = ["status = ?"]
            params = [status.value]

            # Update timestamps based on status
            if status == ExperimentStatus.RUNNING:
                update_fields.append("started_at = ?")
                params.append(datetime.now().isoformat())
            elif status in [
                ExperimentStatus.COMPLETED,
                ExperimentStatus.FAILED,
                ExperimentStatus.CANCELLED,
            ]:
                update_fields.append("completed_at = ?")
                params.append(datetime.now().isoformat())

            params.append(experiment_id)

            cursor.execute(
                f"UPDATE experiments SET {', '.join(update_fields)} WHERE experiment_id = ?",
                params,
            )
            conn.commit()

            return cursor.rowcount > 0

    def record_result(
        self,
        experiment_id: str,
        result: ExperimentResult,
        run_number: int = 1,
    ) -> bool:
        """Record experiment result."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO experiment_results
                (experiment_id, run_number, result_data, created_at)
                VALUES (?, ?, ?, ?)
            """,
                (
                    experiment_id,
                    run_number,
                    json.dumps(result.to_dict()),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

            return cursor.rowcount > 0

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment details."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM experiments WHERE experiment_id = ?",
                (experiment_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            # Parse tags
            tags = []
            if row["tags"]:
                tags = json.loads(row["tags"])

            return {
                "experiment_id": row["experiment_id"],
                "config_id": row["config_id"],
                "config_name": row["config_name"],
                "config_data": json.loads(row["config_data"]),
                "status": row["status"],
                "created_at": row["created_at"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "tags": tags,
            }

    def get_experiment_results(
        self,
        experiment_id: str,
        limit: int = 100,
    ) -> List[ExperimentResult]:
        """Get results for an experiment."""
        results = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM experiment_results
                WHERE experiment_id = ?
                ORDER BY run_number DESC
                LIMIT ?
            """,
                (experiment_id, limit),
            )

            for row in cursor.fetchall():
                result_data = json.loads(row["result_data"])
                result = ExperimentResult.from_dict(result_data)
                results.append(result)

        return results

    def search_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        config_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search for experiments matching criteria."""
        query = "SELECT * FROM experiments WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if config_name:
            query += " AND config_name LIKE ?"
            params.append(f"%{config_name}%")

        if tags:
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')

        query += " ORDER BY created_at DESC"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        experiments = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)

            for row in cursor.fetchall():
                # Parse tags
                tags = []
                if row["tags"]:
                    tags = json.loads(row["tags"])

                experiments.append(
                    {
                        "experiment_id": row["experiment_id"],
                        "config_id": row["config_id"],
                        "config_name": row["config_name"],
                        "status": row["status"],
                        "created_at": row["created_at"],
                        "started_at": row["started_at"],
                        "completed_at": row["completed_at"],
                        "tags": tags,
                    }
                )

        return experiments

    def analyze_experiments(
        self,
        config_id: Optional[str] = None,
        min_quality: float = 0.0,
        max_cost: Optional[float] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Analyze experiment results to find optimal configurations."""
        # Get all experiments with results
        if config_id:
            experiments = self.search_experiments(config_name=config_id, limit=limit)
        else:
            experiments = self.search_experiments(limit=limit)

        analysis = {
            "total_experiments": len(experiments),
            "configurations": {},
            "best_by_quality": None,
            "best_by_cost": None,
            "best_by_cost_quality_ratio": None,
        }

        # Track best configurations
        best_quality_score = 0.0
        best_cost = float("inf")
        best_ratio = float("inf")

        for exp in experiments:
            exp_id = exp["experiment_id"]
            results = self.get_experiment_results(exp_id, limit=100)  # Get more results

            if not results:
                continue

            config = results[0].config  # All results for same experiment have same config

            # Initialize config data if not exists
            if config.config_id not in analysis["configurations"]:
                analysis["configurations"][config.config_id] = {
                    "name": config.name,
                    "total_runs": 0,
                    "successful_runs": 0,
                    "total_cost": 0.0,
                    "total_time": 0.0,
                    "quality_scores": [],
                    "cost_per_quality": [],
                }

            config_data = analysis["configurations"][config.config_id]

            # Process all results for this experiment
            for result in results:
                config_data["total_runs"] += 1

                if result.success and result.evaluation_result:
                    config_data["successful_runs"] += 1
                    config_data["total_cost"] += result.total_cost
                    config_data["total_time"] += result.total_time
                    config_data["quality_scores"].append(result.quality_score)
                    config_data["cost_per_quality"].append(result.cost_per_quality)

                    # Update best configurations
                    if result.quality_score > best_quality_score:
                        best_quality_score = result.quality_score
                        analysis["best_by_quality"] = {
                            "config_id": config.config_id,
                            "config_name": config.name,
                            "quality_score": result.quality_score,
                            "cost": result.total_cost,
                            "time": result.total_time,
                        }

                    if result.total_cost < best_cost:
                        best_cost = result.total_cost
                        analysis["best_by_cost"] = {
                            "config_id": config.config_id,
                            "config_name": config.name,
                            "quality_score": result.quality_score,
                            "cost": result.total_cost,
                            "time": result.total_time,
                        }

                    if result.cost_per_quality < best_ratio:
                        best_ratio = result.cost_per_quality
                        analysis["best_by_cost_quality_ratio"] = {
                            "config_id": config.config_id,
                            "config_name": config.name,
                            "quality_score": result.quality_score,
                            "cost": result.total_cost,
                            "cost_per_quality": result.cost_per_quality,
                            "time": result.total_time,
                        }

        # Calculate averages for each configuration
        for _config_id, data in analysis["configurations"].items():
            if data["successful_runs"] > 0:
                data["avg_quality"] = sum(data["quality_scores"]) / data["successful_runs"]
                data["avg_cost_per_quality"] = sum(data["cost_per_quality"]) / data["successful_runs"]
                data["avg_cost"] = data["total_cost"] / data["successful_runs"]
                data["avg_time"] = data["total_time"] / data["successful_runs"]
            else:
                data["avg_quality"] = 0.0
                data["avg_cost_per_quality"] = 0.0
                data["avg_cost"] = 0.0
                data["avg_time"] = 0.0

        return analysis

    def recommend_configuration(
        self,
        target_quality: float = 70.0,
        max_cost: Optional[float] = None,
        strategy: str = "balanced",
    ) -> Optional[ExperimentConfig]:
        """
        Recommend the best configuration based on historical data.

        Args:
            target_quality: Minimum acceptable quality score
            max_cost: Maximum acceptable cost (None for no limit)
            strategy: "balanced", "quality_first", or "cost_optimized"
        """
        analysis = self.analyze_experiments(limit=500)

        if not analysis["configurations"]:
            return None

        best_config = None
        best_score = float("-inf")

        for config_id, data in analysis["configurations"].items():
            # Skip if not enough successful runs
            if data["successful_runs"] < 3:
                continue

            # Skip if doesn't meet quality requirement
            if data["avg_quality"] < target_quality:
                continue

            # Skip if exceeds cost limit
            if max_cost is not None and data["avg_cost"] > max_cost:
                continue

            # Calculate score based on strategy
            if strategy == "quality_first":
                score = data["avg_quality"]
            elif strategy == "cost_optimized":
                score = -data["avg_cost"]  # Negative because lower cost is better
            else:  # balanced
                # Normalize and combine quality and cost
                # Higher quality and lower cost gives higher score
                quality_norm = data["avg_quality"] / 100.0  # Assuming 0-100 scale
                cost_norm = 1.0 / (data["avg_cost"] + 0.1)  # Avoid division by zero
                score = quality_norm * 0.7 + cost_norm * 0.3

            if score > best_score:
                best_score = score
                # Find the config data
                for exp in self.search_experiments(limit=100):
                    if exp["config_id"] == config_id:
                        config_data = self.get_experiment(exp["experiment_id"])
                        if config_data:
                            best_config = ExperimentConfig.from_dict(config_data["config_data"])
                        break

        return best_config

    def export_results(self, output_path: Path, format: str = "json") -> bool:
        """Export experiment results to file."""
        try:
            # Get all experiments
            experiments = self.search_experiments(limit=1000)

            export_data = {
                "export_date": datetime.now().isoformat(),
                "database_path": str(self.db_path),
                "experiment_count": len(experiments),
                "experiments": [],
            }

            for exp in experiments:
                exp_data = self.get_experiment(exp["experiment_id"])
                if exp_data:
                    results = self.get_experiment_results(exp["experiment_id"])
                    exp_data["results"] = [r.to_dict() for r in results]
                    export_data["experiments"].append(exp_data)

            if format == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                # CSV format could be added here
                raise ValueError(f"Unsupported format: {format}")

            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False

    def cleanup(self, max_age_days: int = 90):
        """Clean up old experiments."""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta

        cutoff_date = cutoff_date - timedelta(days=max_age_days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Delete old experiments
            cursor.execute(
                """
                DELETE FROM experiments
                WHERE created_at < ?
                  AND status IN ('completed', 'failed', 'cancelled')
            """,
                (cutoff_date.isoformat(),),
            )
            deleted_experiments = cursor.rowcount

            # Delete orphaned results
            cursor.execute("""
                DELETE FROM experiment_results
                WHERE experiment_id NOT IN (SELECT experiment_id FROM experiments)
            """)
            deleted_results = cursor.rowcount

            conn.commit()

        return deleted_experiments + deleted_results


# Factory function for easy tracker creation
def create_experiment_tracker(
    db_path: Optional[Path] = None,
) -> ExperimentTracker:
    """Create and configure an experiment tracker."""
    return ExperimentTracker(db_path=db_path)
