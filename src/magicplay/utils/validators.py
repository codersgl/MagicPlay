"""
Data validation utilities.

Provides validation functions for common data types and formats.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.field:
            return f"Validation error in '{self.field}': {self.message}"
        return f"Validation error: {self.message}"


def validate_path(
    path: Union[str, Path],
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_dir: bool = False,
    allowed_extensions: Optional[List[str]] = None,
    field_name: str = "path"
) -> Path:
    """
    Validate a file or directory path.

    Args:
        path: Path to validate
        must_exist: If True, path must exist
        must_be_file: If True, path must be a file
        must_be_dir: If True, path must be a directory
        allowed_extensions: List of allowed file extensions (e.g., ['.jpg', '.png'])
        field_name: Name of field for error messages

    Returns:
        Validated Path object

    Raises:
        ValidationError: If validation fails
    """
    if isinstance(path, str):
        path = Path(path)

    if must_exist and not path.exists():
        raise ValidationError(f"Path does not exist: {path}", field_name)

    if must_be_file and not path.is_file():
        raise ValidationError(f"Path is not a file: {path}", field_name)

    if must_be_dir and not path.is_dir():
        raise ValidationError(f"Path is not a directory: {path}", field_name)

    if allowed_extensions and path.suffix.lower() not in allowed_extensions:
        raise ValidationError(
            f"Invalid file extension: {path.suffix}. "
            f"Allowed: {', '.join(allowed_extensions)}",
            field_name
        )

    return path


def validate_url(url: str, field_name: str = "url") -> str:
    """
    Validate a URL string.

    Args:
        url: URL to validate
        field_name: Name of field for error messages

    Returns:
        Validated URL string

    Raises:
        ValidationError: If validation fails
    """
    # Simple URL pattern
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    if not pattern.match(url):
        raise ValidationError(f"Invalid URL format: {url}", field_name)

    return url


def validate_non_empty_string(
    value: Any,
    min_length: int = 1,
    max_length: Optional[int] = None,
    field_name: str = "value"
) -> str:
    """
    Validate a non-empty string.

    Args:
        value: Value to validate
        min_length: Minimum string length
        max_length: Maximum string length (None for no limit)
        field_name: Name of field for error messages

    Returns:
        Validated string

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, str):
        raise ValidationError(f"Expected string, got {type(value).__name__}", field_name)

    if len(value) < min_length:
        raise ValidationError(
            f"String too short (min {min_length} chars): '{value[:50]}'...",
            field_name
        )

    if max_length and len(value) > max_length:
        raise ValidationError(
            f"String too long (max {max_length} chars): '{value[:50]}'...",
            field_name
        )

    return value


def validate_positive_number(
    value: Any,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    field_name: str = "value"
) -> Union[int, float]:
    """
    Validate a positive number.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Name of field for error messages

    Returns:
        Validated number

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"Expected number, got {type(value).__name__}", field_name)

    if min_value is not None and value < min_value:
        raise ValidationError(
            f"Value {value} is less than minimum {min_value}",
            field_name
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"Value {value} is greater than maximum {max_value}",
            field_name
        )

    return value


def validate_dict_keys(
    data: Dict,
    required_keys: List[str],
    optional_keys: Optional[List[str]] = None,
    field_name: str = "data"
) -> Dict:
    """
    Validate dictionary has required keys.

    Args:
        data: Dictionary to validate
        required_keys: List of required keys
        optional_keys: List of optional keys (for documentation)
        field_name: Name of field for error messages

    Returns:
        Validated dictionary

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValidationError(f"Expected dict, got {type(data).__name__}", field_name)

    missing_keys = [k for k in required_keys if k not in data]
    if missing_keys:
        raise ValidationError(
            f"Missing required keys: {', '.join(missing_keys)}",
            field_name
        )

    return data


def validate_video_duration(
    duration: Any,
    min_duration: int = 1,
    max_duration: int = 60,
    field_name: str = "duration"
) -> int:
    """
    Validate video duration.

    Args:
        duration: Duration value to validate
        min_duration: Minimum duration in seconds
        max_duration: Maximum duration in seconds
        field_name: Name of field for error messages

    Returns:
        Validated duration

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(duration, (int, float)):
        raise ValidationError(f"Expected number, got {type(duration).__name__}", field_name)

    duration = int(duration)

    if duration < min_duration:
        raise ValidationError(
            f"Duration {duration}s is less than minimum {min_duration}s",
            field_name
        )

    if duration > max_duration:
        raise ValidationError(
            f"Duration {duration}s is greater than maximum {max_duration}s",
            field_name
        )

    return duration
