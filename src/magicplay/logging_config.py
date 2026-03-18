"""
MagicPlay Logging Configuration

Centralized logging setup with consistent formatting and handlers.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from magicplay.config import Settings


# Cache for configured logger to avoid redundant configuration
_configured_loggers = set()


def setup_logging(
    settings: Optional[Settings] = None,
    log_file: Optional[Path] = None,
    force: bool = False
) -> None:
    """
    Configure application-wide logging.

    Args:
        settings: Application settings (uses get_settings() if not provided)
        log_file: Optional log file path (overrides settings)
        force: If True, reconfigure even if already configured
    """
    if settings is None:
        from magicplay.config import get_settings
        settings = get_settings()

    # Skip if already configured (unless force=True)
    root_logger_name = logging.getLogger().name
    if root_logger_name in _configured_loggers and not force:
        return

    # Parse log level
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(settings.log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    log_path = log_file or settings.log_file
    if log_path:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _configured_loggers.add(root_logger_name)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__ of the module)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


class LoggingContext:
    """
    Context manager for temporary logging configuration.

    Usage:
        with LoggingContext("DEBUG", log_file="debug.log"):
            # Debug logging enabled in this block
            pass
    """

    def __init__(
        self,
        level: str = "DEBUG",
        log_file: Optional[Path] = None
    ):
        self.level = level
        self.log_file = log_file
        self.original_handlers = None
        self.original_level = None

    def __enter__(self):
        """Save current logging state and apply temporary config."""
        root_logger = logging.getLogger()
        self.original_handlers = root_logger.handlers.copy()
        self.original_level = root_logger.level

        # Clear handlers
        root_logger.handlers.clear()

        # Set new level
        root_logger.setLevel(getattr(logging, self.level.upper(), logging.DEBUG))

        # Add console handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Add file handler if specified
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original logging state."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.handlers.extend(self.original_handlers or [])
        if self.original_level is not None:
            root_logger.setLevel(self.original_level)
