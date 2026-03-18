"""
MagicPlay Configuration Module

Provides centralized, type-safe configuration management using Pydantic.
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
