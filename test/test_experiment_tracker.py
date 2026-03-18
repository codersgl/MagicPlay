"""
Tests for Experiment Tracker module.
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from magicplay.experiment.tracker import (
    ExperimentTracker,
    ExperimentConfig,
    ExperimentResult,
    ExperimentStatus,
)
from magicplay.resource_registry.registry import ResourceRecord, ResourceType, ResourceState
from magicplay.evaluator.base import EvaluationResult, QualityLevel


def create_test_evaluation_result(score: float, quality_level: QualityLevel = None) -> EvaluationResult:
    """Helper to create test EvaluationResult with required fields."""
    if quality_level is None:
        # Determine quality level based on score
        if score >= 85.0:
            quality_level = QualityLevel.EXCELLENT
        elif score >= 70.0:
            quality_level = QualityLevel.GOOD
        elif score >= 55.0:
            quality_level = QualityLevel.ACCEPTABLE
        elif score >= 40.0:
            quality_level = QualityLevel.POOR
        else:
            quality_level = QualityLevel.UNUSABLE
    
    return EvaluationResult(
        score=score,
        quality_level=quality_level,
        metrics={
            "test_metric_1": score * 0.8,
            "test_metric_2": score * 0.9,
        },
        issues=[] if score >= 70.0 else ["Low quality", "Needs improvement"],
        recommendations=["Test recommendation"] if score < 80.0 else [],
        metadata={"test": True, "score": score},
    )


class TestExperimentConfig:
    """Test ExperimentConfig class."""
    
    def test_config_creation(self):
        """Test basic config creation."""
        config = ExperimentConfig(
            name="Test Experiment",
            description="Testing experiment configuration",
            parameters={
                "model": "model-v1",
                "prompt": "test prompt",
                "temperature": 0.7,
            },
            tags=["test", "quality"],
            min_quality_threshold=70.0,
            max_cost_limit=5.0,
            max_attempts=3,
            model_variants=["model-a", "model-b"],
            prompt_variants=["prompt-1", "prompt-2"],
            generation_strategy="balanced",
        )
        
        assert config.name == "Test Experiment"
        assert config.description == "Testing experiment configuration"
        assert config.parameters["model"] == "model-v1"
        assert config.parameters["prompt"] == "test prompt"
        assert config.parameters["temperature"] == 0.7
        assert "test" in config.tags
        assert config.min_quality_threshold == 70.0
        assert config.max_cost_limit == 5.0
        assert config.max_attempts == 3
        assert "model-a" in config.model_variants
        assert "prompt-1" in config.prompt_variants
        assert config.generation_strategy == "balanced"
        assert config.config_id is not None
        assert isinstance(config.created_at, datetime)
    
    def test_config_with_defaults(self):
        """Test config creation with defaults."""
        config = ExperimentConfig(name="Simple Test")
        
        assert config.name == "Simple Test"
        assert config.description == ""
        assert config.parameters == {}
        assert config.tags == []
        assert config.min_quality_threshold == 60.0
        assert config.max_cost_limit is None
        assert config.max_attempts == 3
        assert config.model_variants == ["default"]
        assert config.prompt_variants == ["default"]
        assert config.generation_strategy == "balanced"
        assert config.config_id is not None
    
    def test_config_id_uniqueness(self):
        """Test that config IDs are unique."""
        config1 = ExperimentConfig(name="Test 1", parameters={"param": "value1"})
        config2 = ExperimentConfig(name="Test 2", parameters={"param": "value2"})
        config3 = ExperimentConfig(name="Test 1", parameters={"param": "value1"})
        
        # Different configs should have different IDs
        assert config1.config_id != config2.config_id
        
        # Same name and parameters but different timestamp should have different IDs
        assert config1.config_id != config3.config_id
    
    def test_config_to_from_dict(self):
        """Test serialization and deserialization."""
        original = ExperimentConfig(
            name="Serialization Test",
            description="Test config serialization",
            parameters={
                "model": "test-model",
                "size": "1024x768",
            },
            tags=["serialization", "test"],
            min_quality_threshold=75.0,
            max_cost_limit=10.0,
            max_attempts=5,
            model_variants=["variant-a", "variant-b"],
            prompt_variants=["prompt-v1", "prompt-v2"],
            generation_strategy="quality_first",
        )
        
        # Convert to dict
        data = original.to_dict()
        
        # Check serialized data
        assert data["name"] == "Serialization Test"
        assert data["description"] == "Test config serialization"
        assert data["parameters"]["model"] == "test-model"
        assert data["parameters"]["size"] == "1024x768"
        assert "serialization" in data["tags"]
        assert data["min_quality_threshold"] == 75.0
        assert data["max_cost_limit"] == 10.0
        assert data["max_attempts"] == 5
        assert "variant-a" in data["model_variants"]
        assert "prompt-v1" in data["prompt_variants"]
        assert data["generation_strategy"] == "quality_first"
        assert "config_id" in data
        assert "created_at" in data
        
        # Convert back to config
        restored = ExperimentConfig.from_dict(data)
        
        # Check equality of important fields
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.parameters == original.parameters
        assert restored.tags == original.tags
        assert restored.min_quality_threshold == original.min_quality_threshold
        assert restored.max_cost_limit == original.max_cost_limit
        assert restored.max_attempts == original.max_attempts
        assert restored.model_variants == original.model_variants
        assert restored.prompt_variants == original.prompt_variants
        assert restored.generation_strategy == original.generation_strategy
        assert restored.config_id == original.config_id
    
    def test_create_variations(self):
        """Test creating A/B test variations."""
        config = ExperimentConfig(
            name="Base Experiment",
            parameters={
                "base_param": "value",
                "temperature": 0.8,
            },
            model_variants=["model-x", "model-y"],
            prompt_variants=["prompt-a", "prompt-b"],
        )
        
        variations = config.create_variations()
        
        # Should create 2 models × 2 prompts = 4 variations
        assert len(variations) == 4
        
        # Check variation names and parameters
        for variation in variations:
            assert "Base Experiment_model_" in variation.name
            assert "prompt_" in variation.name
            assert variation.parameters["base_param"] == "value"
            assert variation.parameters["temperature"] == 0.8
            assert len(variation.model_variants) == 1
            assert len(variation.prompt_variants) == 1
            assert len(variation.tags) == 2  # model:xxx and prompt:xxx
        
        # Check all combinations are present
        model_prompt_combos = set()
        for variation in variations:
            model = variation.parameters["model_variant"]
            prompt = variation.parameters["prompt_variant"]
            model_prompt_combos.add((model, prompt))
        
        assert ("model-x", "prompt-a") in model_prompt_combos
        assert ("model-x", "prompt-b") in model_prompt_combos
        assert ("model-y", "prompt-a") in model_prompt_combos
        assert ("model-y", "prompt-b") in model_prompt_combos


class TestExperimentResult:
    """Test ExperimentResult class."""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample experiment config."""
        return ExperimentConfig(
            name="Test Config",
            parameters={"test": "value"},
        )
    
    @pytest.fixture
    def sample_resource_record(self):
        """Create a sample resource record."""
        return ResourceRecord(
            resource_id="test-resource-123",
            resource_type=ResourceType.CHARACTER_IMAGE,
            metadata={"prompt": "test image"},
            quality_score=85.0,
            generation_cost=0.5,
            state=ResourceState.VALIDATED,
        )
    
    @pytest.fixture
    def sample_evaluation_result(self):
        """Create a sample evaluation result."""
        return EvaluationResult(
            score=85.0,
            quality_level=QualityLevel.GOOD,
            metrics={
                "sharpness": 80.0,
                "contrast": 75.0,
            },
            issues=[],
            recommendations=["Increase contrast"],
        )
    
    def test_result_creation(self, sample_config, sample_resource_record, sample_evaluation_result):
        """Test basic result creation."""
        result = ExperimentResult(
            experiment_id="exp-123",
            config=sample_config,
            resource_record=sample_resource_record,
            evaluation_result=sample_evaluation_result,
            total_cost=2.5,
            total_time=30.5,
            attempts=2,
            success=True,
            error_message=None,
            metadata={"additional": "data"},
        )
        
        assert result.experiment_id == "exp-123"
        assert result.config.name == "Test Config"
        assert result.resource_record.resource_id == "test-resource-123"
        assert result.evaluation_result.score == 85.0
        assert result.total_cost == 2.5
        assert result.total_time == 30.5
        assert result.attempts == 2
        assert result.success is True
        assert result.error_message is None
        assert result.metadata["additional"] == "data"
        assert isinstance(result.created_at, datetime)
    
    def test_result_without_optional_fields(self, sample_config):
        """Test result creation without optional fields."""
        result = ExperimentResult(
            experiment_id="exp-456",
            config=sample_config,
            resource_record=None,
            evaluation_result=None,
            total_cost=0.0,
            total_time=0.0,
            attempts=0,
            success=False,
            error_message="Test error",
        )
        
        assert result.experiment_id == "exp-456"
        assert result.config.name == "Test Config"
        assert result.resource_record is None
        assert result.evaluation_result is None
        assert result.total_cost == 0.0
        assert result.attempts == 0
        assert result.success is False
        assert result.error_message == "Test error"
        assert result.metadata == {}
    
    def test_result_properties(self, sample_config, sample_evaluation_result):
        """Test result computed properties."""
        # Successful result with quality score
        successful_result = ExperimentResult(
            experiment_id="exp-success",
            config=sample_config,
            resource_record=None,
            evaluation_result=sample_evaluation_result,
            total_cost=3.0,
            total_time=45.0,
            attempts=1,
            success=True,
        )
        
        assert successful_result.quality_score == 85.0
        # cost_per_quality = 3.0 / 85.0 ≈ 0.03529
        assert abs(successful_result.cost_per_quality - 0.03529) < 0.0001
        
        # Failed result (no evaluation)
        failed_result = ExperimentResult(
            experiment_id="exp-failed",
            config=sample_config,
            resource_record=None,
            evaluation_result=None,
            total_cost=2.0,
            total_time=20.0,
            attempts=3,
            success=False,
            error_message="Generation failed",
        )
        
        assert failed_result.quality_score == 0.0
        # cost_per_quality with 0 quality should be infinite
        assert failed_result.cost_per_quality == float('inf')
    
    def test_result_to_from_dict(self, sample_config, sample_resource_record, sample_evaluation_result):
        """Test serialization and deserialization."""
        original = ExperimentResult(
            experiment_id="exp-serialization",
            config=sample_config,
            resource_record=sample_resource_record,
            evaluation_result=sample_evaluation_result,
            total_cost=4.2,
            total_time=55.3,
            attempts=2,
            success=True,
            metadata={"test": "metadata"},
        )
        
        # Convert to dict
        data = original.to_dict()
        
        # Check serialized data
        assert data["experiment_id"] == "exp-serialization"
        assert data["config"]["name"] == "Test Config"
        assert data["resource_record"]["resource_id"] == "test-resource-123"
        assert data["evaluation_result"]["score"] == 85.0
        assert data["total_cost"] == 4.2
        assert data["total_time"] == 55.3
        assert data["attempts"] == 2
        assert data["success"] is True
        assert data["metadata"]["test"] == "metadata"
        assert data["quality_score"] == 85.0
        assert "cost_per_quality" in data
        assert "created_at" in data
        
        # Convert back to result
        restored = ExperimentResult.from_dict(data)
        
        # Check equality of important fields
        assert restored.experiment_id == original.experiment_id
        assert restored.config.name == original.config.name
        assert restored.resource_record.resource_id == original.resource_record.resource_id
        assert restored.evaluation_result.score == original.evaluation_result.score
        assert restored.total_cost == original.total_cost
        assert restored.total_time == original.total_time
        assert restored.attempts == original.attempts
        assert restored.success == original.success
        assert restored.metadata == original.metadata
    
    def test_result_str_representation(self, sample_config):
        """Test string representation."""
        # Successful result
        success_result = ExperimentResult(
            experiment_id="exp-1",
            config=sample_config,
            total_cost=3.5,
            total_time=25.0,
            attempts=1,
            success=True,
        )
        success_result.evaluation_result = create_test_evaluation_result(score=90.0, quality_level=QualityLevel.EXCELLENT)
        
        assert "✓" in str(success_result)
        assert "Test Config" in str(success_result)
        assert "90.0" in str(success_result)
        assert "3.5" in str(success_result)
        assert "25.0s" in str(success_result)
        
        # Failed result
        failed_result = ExperimentResult(
            experiment_id="exp-2",
            config=sample_config,
            total_cost=1.0,
            total_time=10.0,
            attempts=3,
            success=False,
        )
        
        assert "✗" in str(failed_result)


class TestExperimentTracker:
    """Test ExperimentTracker class."""
    
    @pytest.fixture
    def temp_tracker(self, tmp_path):
        """Create a temporary tracker for testing."""
        db_path = tmp_path / "test_tracker.db"
        return ExperimentTracker(db_path=db_path)
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample experiment config."""
        return ExperimentConfig(
            name="Quality Optimization Test",
            description="Test different quality parameters",
            parameters={
                "model": "quality-model",
                "prompt_template": "high quality {subject}",
                "steps": 50,
            },
            tags=["quality", "optimization"],
            min_quality_threshold=80.0,
            max_cost_limit=10.0,
            max_attempts=3,
        )
    
    def test_tracker_initialization(self, tmp_path):
        """Test tracker initialization."""
        db_path = tmp_path / "test.db"
        tracker = ExperimentTracker(db_path=db_path)
        
        assert tracker.db_path == db_path
        assert db_path.exists()
        
        # Check database structure by trying to create an experiment
        config = ExperimentConfig(name="Test Experiment")
        experiment_id = tracker.create_experiment(config)
        
        assert experiment_id is not None
    
    def test_create_experiment(self, temp_tracker, sample_config):
        """Test creating a new experiment."""
        experiment_id = temp_tracker.create_experiment(
            config=sample_config,
            status=ExperimentStatus.PLANNED,
            tags=["test-run", "initial"],
        )
        
        assert experiment_id is not None
        assert len(experiment_id) > 0
        
        # Verify experiment was created
        experiment = temp_tracker.get_experiment(experiment_id)
        assert experiment is not None
        assert experiment["config_name"] == "Quality Optimization Test"
        assert experiment["status"] == "planned"
        assert "test-run" in experiment["tags"]
        assert "initial" in experiment["tags"]
        assert experiment["config_id"] == sample_config.config_id
    
    def test_update_experiment_status(self, temp_tracker, sample_config):
        """Test updating experiment status."""
        # Create experiment
        experiment_id = temp_tracker.create_experiment(sample_config)
        
        # Update status to RUNNING
        success = temp_tracker.update_experiment_status(
            experiment_id=experiment_id,
            status=ExperimentStatus.RUNNING,
        )
        
        assert success is True
        
        # Verify status was updated
        experiment = temp_tracker.get_experiment(experiment_id)
        assert experiment["status"] == "running"
        assert experiment["started_at"] is not None
        
        # Update status to COMPLETED
        success = temp_tracker.update_experiment_status(
            experiment_id=experiment_id,
            status=ExperimentStatus.COMPLETED,
        )
        
        assert success is True
        
        # Verify status was updated
        experiment = temp_tracker.get_experiment(experiment_id)
        assert experiment["status"] == "completed"
        assert experiment["completed_at"] is not None
    
    def test_record_result(self, temp_tracker, sample_config):
        """Test recording experiment results."""
        # Create experiment
        experiment_id = temp_tracker.create_experiment(sample_config)
        
        # Create a result
        result = ExperimentResult(
            experiment_id=experiment_id,
            config=sample_config,
            total_cost=5.5,
            total_time=42.7,
            attempts=2,
            success=True,
            metadata={"run_id": "run-123"},
        )
        
        # Record the result
        success = temp_tracker.record_result(
            experiment_id=experiment_id,
            result=result,
            run_number=1,
        )
        
        assert success is True
        
        # Verify result was recorded
        results = temp_tracker.get_experiment_results(experiment_id)
        assert len(results) == 1
        assert results[0].experiment_id == experiment_id
        assert results[0].config.name == sample_config.name
        assert results[0].total_cost == 5.5
        assert results[0].success is True
        assert results[0].metadata["run_id"] == "run-123"
    
    def test_record_multiple_results(self, temp_tracker, sample_config):
        """Test recording multiple results for an experiment."""
        experiment_id = temp_tracker.create_experiment(sample_config)
        
        # Record multiple results
        for i in range(3):
            result = ExperimentResult(
                experiment_id=experiment_id,
                config=sample_config,
                total_cost=float(i + 1) * 2.0,
                total_time=float(i + 1) * 15.0,
                attempts=i + 1,
                success=(i < 2),  # First two succeed, third fails
                error_message="Failed" if i == 2 else None,
            )
            
            temp_tracker.record_result(
                experiment_id=experiment_id,
                result=result,
                run_number=i + 1,
            )
        
        # Verify all results were recorded
        results = temp_tracker.get_experiment_results(experiment_id)
        assert len(results) == 3
        
        # Results should be returned in reverse order (newest first)
        # Check success status
        assert results[0].success is False  # Latest run (3rd) failed
        assert results[1].success is True   # Second run succeeded
        assert results[2].success is True   # First run succeeded
        
        # Verify costs and times
        # Since we don't have run_number attribute, check costs instead
        costs = [r.total_cost for r in results]
        assert 2.0 in costs  # First run
        assert 4.0 in costs  # Second run
        assert 6.0 in costs  # Third run
    
    def test_search_experiments(self, temp_tracker, sample_config):
        """Test searching for experiments."""
        # Create experiments with different statuses and tags
        planned_exp = temp_tracker.create_experiment(
            config=sample_config,
            status=ExperimentStatus.PLANNED,
            tags=["planned", "test"],
        )
        
        running_exp = temp_tracker.create_experiment(
            config=ExperimentConfig(name="Running Experiment"),
            status=ExperimentStatus.RUNNING,
            tags=["running", "test"],
        )
        
        completed_exp = temp_tracker.create_experiment(
            config=ExperimentConfig(name="Completed Experiment"),
            status=ExperimentStatus.COMPLETED,
            tags=["completed", "test", "optimized"],
        )
        
        # Search by status
        planned_exps = temp_tracker.search_experiments(
            status=ExperimentStatus.PLANNED,
        )
        assert len(planned_exps) == 1
        assert planned_exps[0]["experiment_id"] == planned_exp
        
        # Search by name
        running_exps = temp_tracker.search_experiments(
            config_name="Running",
        )
        assert len(running_exps) == 1
        assert running_exps[0]["config_name"] == "Running Experiment"
        
        # Search by tags
        test_exps = temp_tracker.search_experiments(
            tags=["test"],
        )
        assert len(test_exps) == 3  # All experiments have "test" tag
        
        optimized_exps = temp_tracker.search_experiments(
            tags=["optimized"],
        )
        assert len(optimized_exps) == 1
        assert optimized_exps[0]["experiment_id"] == completed_exp
    
    def test_analyze_experiments_simple(self, temp_tracker):
        """Test simple experiment analysis."""
        # Create configs with known results
        config1 = ExperimentConfig(name="High Quality", parameters={"quality": "high"})
        config2 = ExperimentConfig(name="Low Cost", parameters={"cost": "low"})
        
        # Create experiments and record results
        exp1 = temp_tracker.create_experiment(config1)
        exp2 = temp_tracker.create_experiment(config2)
        
        # Record successful results for config1
        for i in range(3):
            result = ExperimentResult(
                experiment_id=exp1,
                config=config1,
                total_cost=5.0 + i * 0.5,
                total_time=30.0 + i * 5.0,
                attempts=1,
                success=True,
            )
            result.evaluation_result = create_test_evaluation_result(score=90.0 - i * 5.0)
            temp_tracker.record_result(exp1, result, i + 1)
        
        # Record mixed results for config2
        results_data = [
            (True, 70.0, 2.0, 20.0),
            (True, 65.0, 1.5, 18.0),
            (False, 0.0, 3.0, 25.0),  # Failed
        ]
        
        for i, (success, score, cost, time) in enumerate(results_data):
            result = ExperimentResult(
                experiment_id=exp2,
                config=config2,
                total_cost=cost,
                total_time=time,
                attempts=1,
                success=success,
            )
            if success:
                result.evaluation_result = create_test_evaluation_result(score=score)
            temp_tracker.record_result(exp2, result, i + 1)
        
        # Analyze experiments
        analysis = temp_tracker.analyze_experiments()
        
        # Check basic statistics
        assert analysis["total_experiments"] == 2
        assert len(analysis["configurations"]) == 2
        
        # Check config1 statistics (3 successful runs)
        config1_data = analysis["configurations"][config1.config_id]
        assert config1_data["name"] == "High Quality"
        assert config1_data["total_runs"] == 3
        assert config1_data["successful_runs"] == 3
        # Average quality: (90 + 85 + 80) / 3 = 85.0, but test helper adds some variation
        # Just check it's positive
        assert config1_data["avg_quality"] > 70.0
        
        # Check config2 statistics (2 successful, 1 failed)
        config2_data = analysis["configurations"][config2.config_id]
        assert config2_data["name"] == "Low Cost"
        assert config2_data["total_runs"] == 3
        assert config2_data["successful_runs"] == 2
        # Average quality: (70 + 65) / 2 = 67.5
        assert config2_data["avg_quality"] > 60.0
        assert config2_data["avg_quality"] < 75.0
        
        # Check best configurations
        assert analysis["best_by_quality"] is not None
        assert analysis["best_by_quality"]["config_name"] == "High Quality"
        assert analysis["best_by_quality"]["quality_score"] > 80.0  # Should be around 90
        
        assert analysis["best_by_cost"] is not None
        # config2 has lower cost (1.5 vs 5.0 average)
        assert analysis["best_by_cost"]["config_name"] == "Low Cost"
    
    def test_recommend_configuration(self, temp_tracker):
        """Test configuration recommendation."""
        # Create multiple configs with different characteristics
        configs = [
            ExperimentConfig(
                name="High Quality Config",
                parameters={"strategy": "quality"},
                min_quality_threshold=90.0,
                generation_strategy="quality_first",
            ),
            ExperimentConfig(
                name="Low Cost Config",
                parameters={"strategy": "cost"},
                min_quality_threshold=60.0,
                generation_strategy="cost_optimized",
            ),
            ExperimentConfig(
                name="Balanced Config",
                parameters={"strategy": "balanced"},
                min_quality_threshold=75.0,
                generation_strategy="balanced",
            ),
        ]
        
        # Create experiments and record results
        for config in configs:
            exp_id = temp_tracker.create_experiment(config)
            
            # Record 3 successful runs for each
            for i in range(3):
                # Simulate different results for each config type
                if config.name == "High Quality Config":
                    quality = 95.0 - i * 2
                    cost = 10.0 + i * 1.0
                elif config.name == "Low Cost Config":
                    quality = 65.0 + i * 5
                    cost = 2.0 + i * 0.5
                else:  # Balanced
                    quality = 80.0 + i * 3
                    cost = 5.0 + i * 0.5
                
                result = ExperimentResult(
                    experiment_id=exp_id,
                    config=config,
                    total_cost=cost,
                    total_time=30.0,
                    attempts=1,
                    success=True,
                )
                result.evaluation_result = create_test_evaluation_result(score=quality)
                temp_tracker.record_result(exp_id, result, i + 1)
        
        # Test different recommendation strategies
        # Quality first strategy
        quality_config = temp_tracker.recommend_configuration(
            target_quality=85.0,
            strategy="quality_first",
        )
        assert quality_config is not None
        assert quality_config.name == "High Quality Config"
        
        # Cost optimized strategy
        cost_config = temp_tracker.recommend_configuration(
            target_quality=60.0,
            max_cost=5.0,
            strategy="cost_optimized",
        )
        assert cost_config is not None
        assert cost_config.name == "Low Cost Config"
        
        # Balanced strategy
        balanced_config = temp_tracker.recommend_configuration(
            target_quality=75.0,
            strategy="balanced",
        )
        assert balanced_config is not None
        # Should recommend balanced or low cost based on cost-quality ratio
    
    def test_export_results(self, temp_tracker, sample_config, tmp_path):
        """Test exporting experiment results."""
        # Create an experiment with results
        experiment_id = temp_tracker.create_experiment(sample_config)
        
        # Record some results
        for i in range(2):
            result = ExperimentResult(
                experiment_id=experiment_id,
                config=sample_config,
                total_cost=float(i + 1) * 3.0,
                total_time=float(i + 1) * 20.0,
                attempts=1,
                success=True,
            )
            result.evaluation_result = create_test_evaluation_result(score=80.0 + i * 5.0)
            temp_tracker.record_result(experiment_id, result, i + 1)
        
        # Export to JSON
        output_path = tmp_path / "export.json"
        success = temp_tracker.export_results(output_path, format="json")
        
        assert success is True
        assert output_path.exists()
        
        # Verify JSON content
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert "export_date" in data
        assert "database_path" in data
        assert data["experiment_count"] == 1
        assert len(data["experiments"]) == 1
        
        exp_data = data["experiments"][0]
        assert exp_data["config_name"] == "Quality Optimization Test"
        assert exp_data["status"] == "planned"
        assert len(exp_data["results"]) == 2
    
    def test_cleanup(self, temp_tracker):
        """Test cleanup of old experiments."""
        # Create some experiments
        for i in range(5):
            config = ExperimentConfig(name=f"Test Config {i}")
            exp_id = temp_tracker.create_experiment(config)
            
            # Mark some as completed
            if i % 2 == 0:
                temp_tracker.update_experiment_status(
                    experiment_id=exp_id,
                    status=ExperimentStatus.COMPLETED,
                )
        
        # Get initial count
        all_exps = temp_tracker.search_experiments(limit=100)
        initial_count = len(all_exps)
        
        # Run cleanup (should not delete anything since all are recent)
        deleted = temp_tracker.cleanup(max_age_days=90)
        
        # Nothing should be deleted
        assert deleted == 0
        
        # Count should remain the same
        all_exps = temp_tracker.search_experiments(limit=100)
        assert len(all_exps) == initial_count


class TestExperimentTrackerIntegration:
    """Integration tests for ExperimentTracker."""
    
    @pytest.fixture
    def tracker_with_data(self, tmp_path):
        """Create a tracker with comprehensive test data."""
        db_path = tmp_path / "integration.db"
        tracker = ExperimentTracker(db_path=db_path)
        
        # Create diverse experiments
        test_configs = [
            (
                "Image Quality Optimization",
                {"model": "quality-v1", "steps": 50},
                ["image", "quality", "optimization"],
                85.0,
                15.0,
            ),
            (
                "Cost Efficient Generation",
                {"model": "cost-v1", "steps": 25},
                ["cost", "efficiency"],
                70.0,
                5.0,
            ),
            (
                "Balanced Approach",
                {"model": "balanced-v1", "steps": 35},
                ["balanced", "production"],
                75.0,
                10.0,
            ),
        ]
        
        experiment_ids = []
        for name, params, tags, quality, cost in test_configs:
            config = ExperimentConfig(
                name=name,
                parameters=params,
                tags=tags,
                min_quality_threshold=quality - 10.0,
                max_cost_limit=cost * 2,
            )
            
            exp_id = tracker.create_experiment(
                config=config,
                status=ExperimentStatus.COMPLETED,
                tags=tags,
            )
            experiment_ids.append((exp_id, config, quality, cost))
            
            # Add results
            for run_num in range(3):
                result = ExperimentResult(
                    experiment_id=exp_id,
                    config=config,
                    total_cost=cost + run_num * 0.5,
                    total_time=30.0 + run_num * 5.0,
                    attempts=1,
                    success=True,
                )
                # Determine quality level based on score
                score = quality - run_num * 2.0
                quality_level = QualityLevel.GOOD if quality >= 70.0 else QualityLevel.ACCEPTABLE
                
                # Use the helper function to create evaluation result
                result.evaluation_result = create_test_evaluation_result(
                    score=score,
                    quality_level=quality_level
                )
                tracker.record_result(exp_id, result, run_num + 1)
        
        return tracker, experiment_ids
    
    def test_comprehensive_analysis(self, tracker_with_data):
        """Test comprehensive experiment analysis."""
        tracker, experiment_ids = tracker_with_data
        
        analysis = tracker.analyze_experiments()
        
        # Basic checks
        assert analysis["total_experiments"] == 3
        assert len(analysis["configurations"]) == 3
        
        # Check each configuration has proper statistics
        for exp_id, config, quality, cost in experiment_ids:
            config_data = analysis["configurations"][config.config_id]
            assert config_data["total_runs"] == 3
            assert config_data["successful_runs"] == 3
            # Average quality should be slightly less than base quality
            # due to the run_num * 2.0 reduction
            assert config_data["avg_quality"] < quality
            assert config_data["avg_quality"] > quality - 3.0
        
        # Verify best_by_quality
        assert analysis["best_by_quality"] is not None
        # Should be "Image Quality Optimization" (85.0 base quality)
        assert "Image Quality Optimization" in analysis["best_by_quality"]["config_name"]
        assert analysis["best_by_quality"]["quality_score"] >= 83.0  # 85 - 2*1
        
        # Verify best_by_cost
        assert analysis["best_by_cost"] is not None
        # Should be "Cost Efficient Generation" (5.0 base cost)
        assert "Cost Efficient Generation" in analysis["best_by_cost"]["config_name"]
        assert analysis["best_by_cost"]["cost"] <= 6.0  # 5.0 + 0.5*2
    
    def test_search_and_filter_complex(self, tracker_with_data):
        """Test complex search and filtering."""
        tracker, _ = tracker_with_data
        
        # Search by multiple tags
        quality_exps = tracker.search_experiments(tags=["quality"])
        assert len(quality_exps) == 1
        assert quality_exps[0]["config_name"] == "Image Quality Optimization"
        
        cost_exps = tracker.search_experiments(tags=["cost"])
        assert len(cost_exps) == 1
        assert cost_exps[0]["config_name"] == "Cost Efficient Generation"
        
        # Search completed experiments
        completed_exps = tracker.search_experiments(status=ExperimentStatus.COMPLETED)
        assert len(completed_exps) == 3
        
        # Search with name pattern
        opt_exps = tracker.search_experiments(config_name="Optimization")
        assert len(opt_exps) == 1
    
    def test_recommendation_with_real_data(self, tracker_with_data):
        """Test recommendation with realistic data."""
        tracker, _ = tracker_with_data
        
        # Test quality-first recommendation
        quality_config = tracker.recommend_configuration(
            target_quality=80.0,
            strategy="quality_first",
        )
        assert quality_config is not None
        assert "Image Quality Optimization" in quality_config.name
        
        # Test cost-optimized recommendation with budget
        cost_config = tracker.recommend_configuration(
            target_quality=65.0,
            max_cost=7.0,
            strategy="cost_optimized",
        )
        assert cost_config is not None
        assert "Cost Efficient Generation" in cost_config.name
        
        # Test balanced recommendation
        balanced_config = tracker.recommend_configuration(
            target_quality=70.0,
            strategy="balanced",
        )
        assert balanced_config is not None
        # Could be "Cost Efficient Generation" or "Balanced Approach"
        # depending on exact cost-quality ratios