"""
MagicPlay Base Service

Abstract base class for all external service integrations.
"""

from typing import Optional

from loguru import logger

from magicplay.config import Settings
from magicplay.exceptions import APIError


class BaseService:
    """
    Base class for all external services.

    Provides common functionality:
    - Configuration access
    - Structured logging
    - Health check interface
    - Error handling utilities
    """

    name: str = "base_service"
    version: str = "1.0.0"

    def __init__(self, config: Settings):
        """
        Initialize base service.

        Args:
            config: Application settings
        """
        self.config = config
        self.logger = logger
        self._healthy: Optional[bool] = None

    def _get_api_key(self) -> str:
        """
        Get API key from configuration.

        Subclasses should override to access their specific API key.

        Returns:
            API key string

        Raises:
            APIError: If API key is not configured
        """
        raise NotImplementedError("Subclasses must implement _get_api_key()")

    def health_check(self) -> bool:
        """
        Check if service is operational.

        Default implementation always returns True.
        Subclasses should override with actual health check logic.

        Returns:
            True if service is healthy, False otherwise
        """
        self._healthy = True
        return True

    def is_healthy(self) -> bool:
        """
        Check cached health status.

        Returns:
            True if last health check passed, False otherwise
        """
        return self._healthy is True

    def _raise_api_error(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        """
        Raise a standardized API error.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_body: Raw response body for debugging
        """
        raise APIError(
            message=message,
            service_name=self.name,
            status_code=status_code,
            response_body=response_body,
        )

    def _log_request(self, endpoint: str, payload: dict) -> None:
        """
        Log outgoing request (debug level).

        Args:
            endpoint: API endpoint being called
            payload: Request payload (sanitized)
        """
        self.logger.debug(f"Request to {endpoint}: {self._sanitize_payload(payload)}")

    def _log_response(self, endpoint: str, status: int, data: dict) -> None:
        """
        Log incoming response (debug level).

        Args:
            endpoint: API endpoint
            status: Response status code
            data: Response data (sanitized)
        """
        self.logger.debug(f"Response from {endpoint} [{status}]: {self._sanitize_payload(data)}")

    def _sanitize_payload(self, payload: dict) -> dict:
        """
        Sanitize payload for logging (remove sensitive data).

        Args:
            payload: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        sensitive_keys = {
            "api_key",
            "key",
            "token",
            "secret",
            "password",
            "auth",
        }
        result = {}

        for key, value in payload.items():
            if key.lower() in sensitive_keys:
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                result[key] = self._sanitize_payload(value)
            else:
                result[key] = value

        return result

    def __repr__(self) -> str:
        """String representation of service."""
        return f"{self.__class__.__name__}(name={self.name}, healthy={self._healthy})"
