"""
MagicPlay Generation Context and Result Types

Shared data classes for generator input/output.

Note: Main definitions are in magicplay/ports/generators.py
This module re-exports them for convenient access.
"""

from magicplay.ports.generators import (
    GenerationContext,
    GenerationResult,
    ValidationResult,
)

__all__ = [
    "GenerationContext",
    "GenerationResult",
    "ValidationResult",
]
