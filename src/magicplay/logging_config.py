"""
MagicPlay Loguru Logging Configuration

Centralized logging setup using loguru with consistent formatting,
rotation, and retention policies.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logging(
    log_file: Optional[Path] = None,
    level: str = "INFO",
    rotation: str = "100 MB",
    retention: str = "7 days",
    compression: str = "zip",
) -> None:
    """
    Configure loguru for the application.

    Args:
        log_file: Optional path to log file (enables file logging with rotation)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        rotation: Max size before rotating (e.g., "100 MB", "1 week")
        retention: How long to keep old logs (e.g., "7 days", "1 month")
        compression: Compression format for rotated logs (e.g., "zip", "gz")
    """
    # Remove default handler
    logger.remove()

    # Console handler with color formatting
    logger.add(
        sink=sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # File handler with rotation (if log_file specified)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            sink=str(log_file),
            level=level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            format=("{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"),
        )


def get_logger(name: str = None):
    """
    Get a logger instance.

    With loguru, you typically just use `from loguru import logger`.
    This function exists for compatibility with legacy code.

    Args:
        name: Ignored (kept for backward compatibility)

    Returns:
        The global loguru logger
    """
    return logger
