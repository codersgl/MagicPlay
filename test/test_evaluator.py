"""
Tests for quality evaluation module.
"""

from pathlib import Path
from typing import Any, Union
from unittest.mock import patch

import pytest
from PIL import Image

from magicplay.evaluator.base import (
    BaseEvaluator,
    EvaluationResult,
    QualityLevel,
)
from magicplay.evaluator.image_evaluator import ImageQualityEvaluator


class ConcreteTestEvaluator(BaseEvaluator):
    """Concrete test implementation of BaseEvaluator for testing."""

    def __init__(self):
        super().__init__(name="TestEvaluator", version="1.0")

    def evaluate(self, input_data: Union[str, Path, Any], **kwargs) -> EvaluationResult:
        """Test implementation of evaluate method."""
        # Simple test implementation
        return EvaluationResult(
            score=50.0,
            quality_level=QualityLevel.ACCEPTABLE,
            metrics={"test": 50.0},
            issues=[],
            recommendations=[],
        )


class TestBaseEvaluator:
    """Test BaseEvaluator functionality."""

    def test_base_evaluator_creation(self):
        """Test BaseEvaluator initialization."""
        evaluator = ConcreteTestEvaluator()

        assert evaluator.name == "TestEvaluator"
        assert evaluator.version == "1.0"

    def test_base_evaluator_evaluate_implemented(self):
        """Test that evaluate method is implemented in concrete class."""
        evaluator = ConcreteTestEvaluator()

        result = evaluator.evaluate("test_input")

        assert isinstance(result, EvaluationResult)
        assert result.score == 50.0

    def test_base_evaluator_validate_input_valid_path(self, tmp_path):
        """Test input validation with valid file path."""
        evaluator = ConcreteTestEvaluator()

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        is_valid, error_msg = evaluator.validate_input(str(test_file))

        assert is_valid is True
        assert error_msg is None

    def test_base_evaluator_validate_input_invalid_path(self):
        """Test input validation with invalid file path."""
        evaluator = ConcreteTestEvaluator()

        is_valid, error_msg = evaluator.validate_input("/nonexistent/path/file.txt")

        assert is_valid is False
        assert "does not exist" in error_msg

    def test_base_evaluator_calculate_score(self):
        """Test score calculation with weights."""
        evaluator = ConcreteTestEvaluator()

        metrics = {
            "metric1": 80.0,
            "metric2": 60.0,
            "metric3": 90.0,
        }
        weights = {
            "metric1": 0.5,
            "metric2": 0.3,
            "metric3": 0.2,
        }

        score = evaluator._calculate_score(metrics, weights)

        # Expected: (80*0.5 + 60*0.3 + 90*0.2) = 40 + 18 + 18 = 76
        assert score == 76.0

    def test_base_evaluator_calculate_score_missing_metric(self):
        """Test score calculation with missing metric."""
        evaluator = ConcreteTestEvaluator()

        metrics = {
            "metric1": 80.0,
            "metric2": 60.0,
        }
        weights = {
            "metric1": 0.5,
            "metric2": 0.3,
            "metric3": 0.2,  # metric3 not in metrics
        }

        score = evaluator._calculate_score(metrics, weights)

        # metric3 weight should be ignored
        # Expected: (80*0.5 + 60*0.3) / (0.5+0.3) = (40 + 18) / 0.8 = 72.5
        assert score == 72.5

    def test_base_evaluator_determine_quality_level(self):
        """Test quality level determination."""
        evaluator = ConcreteTestEvaluator()

        # Test different score ranges based on thresholds defined in BaseEvaluator:
        # EXCELLENT >= 85.0, GOOD >= 70.0, ACCEPTABLE >= 55.0, POOR >= 40.0, UNUSABLE < 40.0
        assert evaluator._determine_quality_level(95.0) == QualityLevel.EXCELLENT
        assert evaluator._determine_quality_level(85.0) == QualityLevel.EXCELLENT  # 85 is threshold for EXCELLENT
        assert evaluator._determine_quality_level(80.0) == QualityLevel.GOOD  # 70-85 is GOOD
        assert evaluator._determine_quality_level(75.0) == QualityLevel.GOOD
        assert evaluator._determine_quality_level(65.0) == QualityLevel.ACCEPTABLE  # 55-70 is ACCEPTABLE
        assert evaluator._determine_quality_level(60.0) == QualityLevel.ACCEPTABLE
        assert evaluator._determine_quality_level(55.0) == QualityLevel.ACCEPTABLE  # threshold for ACCEPTABLE
        assert evaluator._determine_quality_level(50.0) == QualityLevel.POOR  # 40-55 is POOR
        assert evaluator._determine_quality_level(45.0) == QualityLevel.POOR  # 40-55 is POOR
        assert evaluator._determine_quality_level(40.0) == QualityLevel.POOR  # threshold for POOR
        assert evaluator._determine_quality_level(35.0) == QualityLevel.UNUSABLE  # < 40 is UNUSABLE
        assert evaluator._determine_quality_level(10.0) == QualityLevel.UNUSABLE
        assert evaluator._determine_quality_level(0.0) == QualityLevel.UNUSABLE

    def test_base_evaluator_is_acceptable(self):
        """Test acceptability check for different quality levels."""
        # Create evaluation results
        excellent_result = EvaluationResult(
            score=95.0,
            quality_level=QualityLevel.EXCELLENT,
            metrics={},
            issues=[],
            recommendations=[],
        )

        good_result = EvaluationResult(
            score=85.0,
            quality_level=QualityLevel.GOOD,
            metrics={},
            issues=[],
            recommendations=[],
        )

        poor_result = EvaluationResult(
            score=40.0,
            quality_level=QualityLevel.POOR,
            metrics={},
            issues=["many issues"],
            recommendations=[],
        )

        assert excellent_result.is_acceptable is True
        assert good_result.is_acceptable is True
        assert poor_result.is_acceptable is False


class TestImageQualityEvaluator:
    """Test ImageQualityEvaluator functionality."""

    def test_image_evaluator_creation(self):
        """Test ImageQualityEvaluator initialization."""
        evaluator = ImageQualityEvaluator()

        assert evaluator.name == "ImageQualityEvaluator"
        assert evaluator.version == "1.0"
        assert "sharpness" in evaluator.metric_weights
        assert "contrast" in evaluator.metric_weights
        assert sum(evaluator.metric_weights.values()) == pytest.approx(1.0)

    def test_image_evaluator_validate_input_pil_image(self):
        """Test input validation with PIL Image."""
        evaluator = ImageQualityEvaluator()

        # Create a test PIL Image
        test_image = Image.new("RGB", (100, 100), color="red")

        is_valid, error_msg = evaluator.validate_input(test_image)

        assert is_valid is True
        assert error_msg is None

    def test_image_evaluator_validate_input_file_path(self, tmp_path):
        """Test input validation with image file path."""
        evaluator = ImageQualityEvaluator()

        # Create a test image file
        test_image = Image.new("RGB", (100, 100), color="blue")
        test_path = tmp_path / "test.png"
        test_image.save(test_path)

        is_valid, error_msg = evaluator.validate_input(str(test_path))

        assert is_valid is True
        assert error_msg is None

    def test_image_evaluator_evaluate_image_path(self, tmp_path):
        """Test evaluating an image from file path."""
        evaluator = ImageQualityEvaluator()

        # Create a test image
        test_image = Image.new("RGB", (512, 512), color="green")
        test_path = tmp_path / "test.png"
        test_image.save(test_path)

        # Mock the internal metrics calculation to avoid scipy dependency
        with patch.object(evaluator, "_calculate_image_metrics") as mock_metrics:
            mock_metrics.return_value = {
                "sharpness": 70.0,
                "contrast": 65.0,
                "brightness": 60.0,
                "color_variance": 55.0,
                "noise_level": 80.0,
                "blur_detection": 75.0,
                "width": 512.0,
                "height": 512.0,
                "aspect_ratio": 1.0,
            }

            result = evaluator.evaluate(str(test_path))

            assert isinstance(result, EvaluationResult)
            assert 0.0 <= result.score <= 100.0
            assert result.quality_level in QualityLevel
            assert isinstance(result.issues, list)
            assert isinstance(result.recommendations, list)
            assert "image_hash" in result.metadata

    def test_image_evaluator_evaluate_pil_image(self):
        """Test evaluating a PIL Image directly."""
        evaluator = ImageQualityEvaluator()

        # Create a test PIL Image
        test_image = Image.new("RGB", (256, 256), color="yellow")

        # Mock the internal metrics calculation
        with patch.object(evaluator, "_calculate_image_metrics") as mock_metrics:
            mock_metrics.return_value = {
                "sharpness": 50.0,
                "contrast": 55.0,
                "brightness": 50.0,
                "color_variance": 45.0,
                "noise_level": 70.0,
                "blur_detection": 65.0,
                "width": 256.0,
                "height": 256.0,
                "aspect_ratio": 1.0,
            }

            result = evaluator.evaluate(test_image)

            assert isinstance(result, EvaluationResult)
            assert 0.0 <= result.score <= 100.0
            assert result.quality_level in QualityLevel

    def test_image_evaluator_evaluate_invalid_input(self):
        """Test evaluating with invalid input."""
        evaluator = ImageQualityEvaluator()

        result = evaluator.evaluate("/nonexistent/path/image.jpg")

        assert isinstance(result, EvaluationResult)
        assert result.score == 0.0
        assert result.quality_level == QualityLevel.UNUSABLE
        assert "does not exist" in str(result.issues)

    def test_image_evaluator_evaluate_exception_handling(self):
        """Test exception handling during evaluation."""
        evaluator = ImageQualityEvaluator()

        # Create a mock that raises an exception when convert is called
        # We need to mock more thoroughly because PIL tries to open the mock
        with patch.object(evaluator, "_calculate_image_metrics") as mock_metrics:
            mock_metrics.side_effect = Exception("Test error in evaluation")

            # Create a simple test image that will trigger the exception
            test_image = Image.new("RGB", (100, 100), color="red")

            result = evaluator.evaluate(test_image)

            assert isinstance(result, EvaluationResult)
            assert result.score == 0.0
            assert result.quality_level == QualityLevel.UNUSABLE
            # The error message should contain our test error
            assert any("Test error" in issue for issue in result.issues)

    def test_image_evaluator_identify_issues(self):
        """Test issue identification from metrics."""
        evaluator = ImageQualityEvaluator()

        # Test metrics that should trigger issues
        low_quality_metrics = {
            "sharpness": 25.0,  # Too low
            "contrast": 20.0,  # Too low
            "brightness": 35.0,  # Too low
            "color_variance": 30.0,
            "noise_level": 35.0,  # Too low (high noise)
            "blur_detection": 25.0,  # Too low (blurry)
            "width": 256.0,  # Too small
            "height": 256.0,
            "aspect_ratio": 1.0,
        }

        issues = evaluator._identify_issues(low_quality_metrics, 30.0)

        assert len(issues) > 0
        assert any("清晰度不足" in issue or "图像模糊" in issue for issue in issues)
        assert any("对比度过低" in issue for issue in issues)
        assert any("图像过暗" in issue for issue in issues)
        assert any("噪点过多" in issue for issue in issues)
        assert any("分辨率过低" in issue for issue in issues)

    def test_image_evaluator_generate_recommendations(self):
        """Test recommendation generation."""
        evaluator = ImageQualityEvaluator()

        # Test with low quality metrics
        low_quality_metrics = {
            "sharpness": 25.0,
            "contrast": 30.0,
            "brightness": 40.0,
            "color_variance": 35.0,
            "noise_level": 35.0,
            "blur_detection": 30.0,
            "width": 256.0,
            "height": 256.0,
            "aspect_ratio": 1.0,
        }

        issues = [
            "图像模糊，清晰度不足",
            "对比度过低，图像看起来平淡",
            "噪点过多，图像质量下降",
            "图像分辨率过低，建议使用更高分辨率",
        ]

        recommendations = evaluator._generate_recommendations(low_quality_metrics, issues)

        assert len(recommendations) > 0
        assert any("清晰度" in rec for rec in recommendations)
        assert any("对比度" in rec for rec in recommendations)
        assert any("降噪" in rec for rec in recommendations)
        assert any("分辨率" in rec for rec in recommendations)

    def test_image_evaluator_calculate_image_hash(self, tmp_path):
        """Test image hash calculation."""
        evaluator = ImageQualityEvaluator()

        # Create a test image file
        test_image = Image.new("RGB", (100, 100), color="red")
        test_path = tmp_path / "test.png"
        test_image.save(test_path)

        image_hash = evaluator._calculate_image_hash(test_path)

        # Hash should be a 32-character hex string
        assert isinstance(image_hash, str)
        assert len(image_hash) == 32
        assert all(c in "0123456789abcdef" for c in image_hash)

    def test_image_evaluator_error_result_creation(self):
        """Test error result creation."""
        evaluator = ImageQualityEvaluator()

        error_message = "Test error message"
        result = evaluator._create_error_result(error_message)

        assert isinstance(result, EvaluationResult)
        assert result.score == 0.0
        assert result.quality_level == QualityLevel.UNUSABLE
        assert "Test error message" in str(result.issues)
        assert "检查图像文件格式和完整性" in result.recommendations

    @pytest.mark.parametrize(
        "width,height,expected_ratio",
        [
            (800, 600, 800 / 600),
            (1920, 1080, 1920 / 1080),
            (1000, 1000, 1.0),
            (0, 100, 0.0),  # Edge case
        ],
    )
    def test_image_evaluator_calculate_metrics_dimensions(self, width, height, expected_ratio):
        """Test dimension metrics calculation."""
        evaluator = ImageQualityEvaluator()

        # Create test image
        test_image = Image.new("RGB", (width, height), color="white")

        # Mock the complex calculations but keep dimension calculations
        with (
            patch.object(evaluator, "_calculate_sharpness", return_value=50.0),
            patch.object(evaluator, "_calculate_contrast", return_value=50.0),
            patch.object(evaluator, "_calculate_brightness", return_value=50.0),
            patch.object(evaluator, "_calculate_color_variance", return_value=50.0),
            patch.object(evaluator, "_calculate_noise_level", return_value=50.0),
            patch.object(evaluator, "_calculate_blur_detection", return_value=50.0),
        ):
            metrics = evaluator._calculate_image_metrics(test_image)

            assert metrics["width"] == float(width)
            assert metrics["height"] == float(height)
            if height > 0:
                assert metrics["aspect_ratio"] == pytest.approx(expected_ratio)
            else:
                assert metrics["aspect_ratio"] == 0.0

    def test_image_evaluator_with_scipy_available(self):
        """Test evaluator when scipy is available."""
        try:
            pass

            scipy_available = True
        except ImportError:
            scipy_available = False

        if not scipy_available:
            pytest.skip("scipy not available")

        evaluator = ImageQualityEvaluator()

        # Create a simple test image
        test_image = Image.new("RGB", (100, 100), color="red")

        # This should work without mocking when scipy is available
        metrics = evaluator._calculate_image_metrics(test_image)

        # Check all metrics are present and within reasonable ranges
        assert "sharpness" in metrics
        assert "contrast" in metrics
        assert "brightness" in metrics
        assert "color_variance" in metrics
        assert "noise_level" in metrics
        assert "blur_detection" in metrics
        assert metrics["width"] == 100.0
        assert metrics["height"] == 100.0
        assert metrics["aspect_ratio"] == 1.0

        # All scores should be between 0 and 100
        for key, value in metrics.items():
            if key not in ["width", "height", "aspect_ratio"]:
                assert 0.0 <= value <= 100.0
