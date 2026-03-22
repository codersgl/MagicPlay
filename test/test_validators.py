"""
Tests for validation utilities.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from magicplay.utils.validators import (
    ValidationError,
    validate_dict_keys,
    validate_non_empty_string,
    validate_path,
    validate_positive_number,
    validate_url,
    validate_video_duration,
)


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_with_field(self):
        """Test error with field name."""
        error = ValidationError("test message", field="test_field")
        assert error.message == "test message"
        assert error.field == "test_field"
        assert "test_field" in str(error)

    def test_validation_error_without_field(self):
        """Test error without field name."""
        error = ValidationError("test message")
        assert error.message == "test message"
        assert error.field is None
        assert "test message" in str(error)


class TestValidatePath:
    """Test path validation."""

    def test_validate_path_string_conversion(self):
        """Test that string paths are converted to Path objects."""
        result = validate_path("/some/path")
        assert isinstance(result, Path)

    def test_validate_path_passing_valid(self):
        """Test validation passes for valid path."""
        with tempfile.NamedTemporaryFile() as f:
            result = validate_path(f.name, must_exist=True, must_be_file=True)
            assert isinstance(result, Path)

    def test_validate_path_must_exist_fails(self):
        """Test validation fails when path must exist but doesn't."""
        with pytest.raises(ValidationError) as exc_info:
            validate_path("/nonexistent/path/xyz", must_exist=True)
        assert "does not exist" in str(exc_info.value)

    def test_validate_path_must_be_file_fails_for_dir(self):
        """Test validation fails when path must be file but is directory."""
        with pytest.raises(ValidationError) as exc_info:
            validate_path("/", must_be_file=True)
        assert "not a file" in str(exc_info.value)

    def test_validate_path_must_be_dir_fails_for_file(self):
        """Test validation fails when path must be directory but is file."""
        with tempfile.NamedTemporaryFile() as f:
            with pytest.raises(ValidationError) as exc_info:
                validate_path(f.name, must_be_dir=True)
            assert "not a directory" in str(exc_info.value)

    def test_validate_path_allowed_extensions(self):
        """Test file extension validation."""
        with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
            result = validate_path(f.name, allowed_extensions=[".jpg", ".png"])
            assert result.suffix == ".jpg"

    def test_validate_path_invalid_extension(self):
        """Test validation fails for invalid extension."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            with pytest.raises(ValidationError) as exc_info:
                validate_path(f.name, allowed_extensions=[".jpg", ".png"])
            assert "Invalid file extension" in str(exc_info.value)


class TestValidateUrl:
    """Test URL validation."""

    def test_validate_url_valid_https(self):
        """Test validation passes for valid HTTPS URL."""
        result = validate_url("https://example.com/path")
        assert result == "https://example.com/path"

    def test_validate_url_valid_http(self):
        """Test validation passes for valid HTTP URL."""
        result = validate_url("http://example.com")
        assert result == "http://example.com"

    def test_validate_url_with_port(self):
        """Test validation passes for URL with port."""
        result = validate_url("http://example.com:8080/path")
        assert result == "http://example.com:8080/path"

    def test_validate_url_localhost(self):
        """Test validation passes for localhost."""
        result = validate_url("http://localhost:3000")
        assert result == "http://localhost:3000"

    def test_validate_url_invalid_no_scheme(self):
        """Test validation fails for URL without scheme."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("example.com")
        assert "Invalid URL format" in str(exc_info.value)

    def test_validate_url_invalid_format(self):
        """Test validation fails for invalid URL format."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("not a url")
        assert "Invalid URL format" in str(exc_info.value)


class TestValidateNonEmptyString:
    """Test non-empty string validation."""

    def test_validate_non_empty_string_valid(self):
        """Test validation passes for valid string."""
        result = validate_non_empty_string("hello")
        assert result == "hello"

    def test_validate_non_empty_string_min_length(self):
        """Test validation respects min_length."""
        result = validate_non_empty_string("hello", min_length=3)
        assert result == "hello"

    def test_validate_non_empty_string_below_min(self):
        """Test validation fails for string below min length."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string("hi", min_length=3)
        assert "too short" in str(exc_info.value)

    def test_validate_non_empty_string_max_length(self):
        """Test validation respects max_length."""
        result = validate_non_empty_string("hi", max_length=5)
        assert result == "hi"

    def test_validate_non_empty_string_above_max(self):
        """Test validation fails for string above max length."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string("hello world", max_length=5)
        assert "too long" in str(exc_info.value)

    def test_validate_non_empty_string_not_string(self):
        """Test validation fails for non-string input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty_string(123)
        assert "Expected string" in str(exc_info.value)


class TestValidatePositiveNumber:
    """Test positive number validation."""

    def test_validate_positive_number_int(self):
        """Test validation passes for integer."""
        result = validate_positive_number(5)
        assert result == 5

    def test_validate_positive_number_float(self):
        """Test validation passes for float."""
        result = validate_positive_number(5.5)
        assert result == 5.5

    def test_validate_positive_number_min(self):
        """Test validation respects min_value."""
        result = validate_positive_number(10, min_value=5)
        assert result == 10

    def test_validate_positive_number_below_min(self):
        """Test validation fails for value below min."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_number(3, min_value=5)
        assert "less than minimum" in str(exc_info.value)

    def test_validate_positive_number_max(self):
        """Test validation respects max_value."""
        result = validate_positive_number(10, max_value=20)
        assert result == 10

    def test_validate_positive_number_above_max(self):
        """Test validation fails for value above max."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_number(25, max_value=20)
        assert "greater than maximum" in str(exc_info.value)

    def test_validate_positive_number_not_number(self):
        """Test validation fails for non-number input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_number("5")
        assert "Expected number" in str(exc_info.value)


class TestValidateDictKeys:
    """Test dictionary keys validation."""

    def test_validate_dict_keys_valid(self):
        """Test validation passes for dict with required keys."""
        data = {"key1": "value1", "key2": "value2"}
        result = validate_dict_keys(data, required_keys=["key1"])
        assert result == data

    def test_validate_dict_keys_multiple_required(self):
        """Test validation passes when all required keys present."""
        data = {"key1": "value1", "key2": "value2"}
        result = validate_dict_keys(data, required_keys=["key1", "key2"])
        assert result == data

    def test_validate_dict_keys_missing(self):
        """Test validation fails for missing keys."""
        data = {"key1": "value1"}
        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys(data, required_keys=["key1", "key2"])
        assert "Missing required keys" in str(exc_info.value)

    def test_validate_dict_keys_not_dict(self):
        """Test validation fails for non-dict input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_dict_keys("not a dict", required_keys=["key1"])
        assert "Expected dict" in str(exc_info.value)


class TestValidateVideoDuration:
    """Test video duration validation."""

    def test_validate_video_duration_int(self):
        """Test validation passes for integer duration."""
        result = validate_video_duration(30)
        assert result == 30

    def test_validate_video_duration_float(self):
        """Test validation passes for float duration."""
        result = validate_video_duration(5.5)
        assert result == 5  # Converted to int (truncated)

    def test_validate_video_duration_min(self):
        """Test validation respects min_duration."""
        result = validate_video_duration(5, min_duration=1)
        assert result == 5

    def test_validate_video_duration_below_min(self):
        """Test validation fails for duration below minimum."""
        with pytest.raises(ValidationError) as exc_info:
            validate_video_duration(0, min_duration=1)
        assert "less than minimum" in str(exc_info.value)

    def test_validate_video_duration_max(self):
        """Test validation respects max_duration."""
        result = validate_video_duration(30, max_duration=60)
        assert result == 30

    def test_validate_video_duration_above_max(self):
        """Test validation fails for duration above maximum."""
        with pytest.raises(ValidationError) as exc_info:
            validate_video_duration(120, max_duration=60)
        assert "greater than maximum" in str(exc_info.value)

    def test_validate_video_duration_not_number(self):
        """Test validation fails for non-number input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_video_duration("30")
        assert "Expected number" in str(exc_info.value)
