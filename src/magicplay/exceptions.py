"""
MagicPlay Custom Exceptions

Centralized exception hierarchy for consistent error handling.
"""

from typing import Any, Dict, Optional


class MagicPlayError(Exception):
    """Base exception for all MagicPlay errors."""

    def __init__(
        self,
        message: str = "An error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(MagicPlayError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, setting_name: Optional[str] = None):
        details = {"setting_name": setting_name} if setting_name else {}
        super().__init__(message, details)


class GenerationError(MagicPlayError):
    """Raised when content generation fails."""

    def __init__(
        self,
        message: str,
        generator_type: Optional[str] = None,
        attempt: Optional[int] = None,
    ):
        details = {}
        if generator_type:
            details["generator_type"] = generator_type
        if attempt:
            details["attempt"] = attempt
        super().__init__(message, details)


class APIError(MagicPlayError):
    """Raised when external API call fails."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        details = {}
        if service_name:
            details["service_name"] = service_name
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body
        super().__init__(message, details)


class ValidationError(MagicPlayError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None,
    ):
        details = {}
        if field_name:
            details["field_name"] = field_name
        if invalid_value is not None:
            details["invalid_value"] = str(invalid_value)
        super().__init__(message, details)


class ResourceNotFoundError(MagicPlayError):
    """Raised when a required resource is not found."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_path: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_path:
            details["resource_path"] = resource_path
        super().__init__(message, details)


class FileOperationError(MagicPlayError):
    """Raised when file operation fails."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        details = {}
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        super().__init__(message, details)


class QualityCheckError(MagicPlayError):
    """Raised when quality evaluation fails."""

    def __init__(
        self,
        message: str,
        quality_score: Optional[float] = None,
        threshold: Optional[float] = None,
    ):
        details = {}
        if quality_score is not None:
            details["quality_score"] = quality_score
        if threshold is not None:
            details["threshold"] = threshold
        super().__init__(message, details)


class WorkflowError(MagicPlayError):
    """Raised when workflow execution fails."""

    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        step: Optional[str] = None,
    ):
        details = {}
        if workflow_id:
            details["workflow_id"] = workflow_id
        if step:
            details["step"] = step
        super().__init__(message, details)
