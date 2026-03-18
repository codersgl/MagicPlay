"""
Retry utilities for API calls.

Provides decorators for automatic retry with exponential backoff.
"""

from functools import wraps
from typing import Callable, Optional, Tuple, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_log,
    after_log,
)

import logging


def api_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    logger_name: Optional[str] = None,
) -> Callable:
    """
    Decorator for API retry with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exceptions: Tuple of exception types that trigger retry
        logger_name: Name of logger for retry logging (uses root logger if None)

    Returns:
        Decorated function with retry behavior

    Usage:
        @api_retry(max_attempts=3)
        def call_api():
            ...
    """
    logger = logging.getLogger(logger_name) if logger_name else None

    decorator_args = {
        "stop": stop_after_attempt(max_attempts),
        "wait": wait_exponential(multiplier=base_delay, max=max_delay),
        "retry": retry_if_exception_type(exceptions),
        "reraise": True,
    }

    if logger:
        decorator_args["before"] = before_log(logger, logging.DEBUG)
        decorator_args["after"] = after_log(logger, logging.DEBUG)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Apply tenacity retry
        retry_func = retry(**decorator_args)(wrapper)
        return retry_func

    return decorator


def with_fallback(
    fallback_value=None,
    fallback_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_fallback: bool = True,
) -> Callable:
    """
    Decorator that provides a fallback value if function raises an exception.

    Args:
        fallback_value: Value to return on failure
        fallback_exceptions: Exception types to catch
        log_fallback: Whether to log fallback events

    Returns:
        Decorated function with fallback behavior

    Usage:
        @with_fallback(fallback_value="default", log_fallback=True)
        def risky_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except fallback_exceptions as e:
                if log_fallback:
                    logger = logging.getLogger(func.__module__)
                    logger.warning(
                        f"{func.__name__} failed, using fallback: {e}"
                    )
                return fallback_value
        return wrapper
    return decorator
