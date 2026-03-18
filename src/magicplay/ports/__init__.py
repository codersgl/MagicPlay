"""
MagicPlay Ports/Interfaces Module

Defines abstract interfaces (protocols) for dependency inversion.
"""

from .generators import IGenerator, GenerationContext, GenerationResult
from .services import ILLMService, IImageService, IVideoService
from .repositories import IRepository

__all__ = [
    # Generators
    "IGenerator",
    "GenerationContext",
    "GenerationResult",
    # Services
    "ILLMService",
    "IImageService",
    "IVideoService",
    # Repositories
    "IRepository",
]
