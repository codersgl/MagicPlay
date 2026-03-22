"""
MagicPlay Ports/Interfaces Module

Defines abstract interfaces (protocols) for dependency inversion.
"""

from .generators import GenerationContext, GenerationResult, IGenerator
from .repositories import IRepository
from .services import IImageService, ILLMService, IVideoService

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
