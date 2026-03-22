"""
MagicPlay Generator Interfaces

Abstract base classes and protocols for all generators.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generic, Optional, TypeVar

# Type variable for generic result type
T = TypeVar("T")


@dataclass
class GenerationContext:
    """
    Context for content generation.

    Contains all necessary information for generators to produce content.
    """

    # Identification
    story_name: str
    episode_name: str
    scene_name: str = ""

    # Context information
    story_context: str = ""
    episode_context: str = ""
    memory: str = ""
    scene_prompt: str = ""

    # Optional context
    previous_frame: Optional[Path] = None
    character_images: Dict[str, Path] = field(default_factory=dict)
    reference_images: Dict[str, Path] = field(default_factory=dict)

    # Generation parameters
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "story_name": self.story_name,
            "episode_name": self.episode_name,
            "scene_name": self.scene_name,
            "story_context": self.story_context,
            "episode_context": self.episode_context,
            "memory": self.memory,
            "scene_prompt": self.scene_prompt,
            "previous_frame": (str(self.previous_frame) if self.previous_frame else None),
            "character_images": {k: str(v) for k, v in self.character_images.items()},
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass
class GenerationResult(Generic[T]):
    """
    Result of a generation operation.

    Generic over the data type T (e.g., str for scripts, Path for images).
    """

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if generation was successful."""
        return self.success

    @property
    def has_data(self) -> bool:
        """Check if result contains data."""
        return self.data is not None

    @property
    def has_warnings(self) -> bool:
        """Check if result has warnings."""
        return len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": (str(self.data) if isinstance(self.data, Path) else self.data),
            "error": self.error,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def ok(cls, data: T, **kwargs) -> "GenerationResult[T]":
        """Create successful result."""
        return cls(success=True, data=data, **kwargs)

    @classmethod
    def fail(cls, error: str, **kwargs) -> "GenerationResult[T]":
        """Create failed result."""
        return cls(success=False, error=error, **kwargs)


@dataclass
class ValidationResult:
    """Result of content validation."""

    is_valid: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def has_issues(self) -> bool:
        """Check if validation found any issues."""
        return len(self.issues) > 0


class IGenerator(ABC, Generic[T]):
    """
    Abstract base class for all generators.

    All generators should inherit from this class or implement its interface.
    """

    name: str = "base_generator"
    description: str = "Base generator class"

    @abstractmethod
    def generate(self, context: GenerationContext) -> GenerationResult[T]:
        """
        Generate content from the given context.

        Args:
            context: Generation context with all necessary information

        Returns:
            GenerationResult containing generated content or error
        """

    def validate(self, result: GenerationResult[T]) -> ValidationResult:
        """
        Validate generated content.

        Default implementation checks if result is successful and has data.
        Subclasses should override for specific validation logic.

        Args:
            result: Generation result to validate

        Returns:
            ValidationResult with validation details
        """
        if not result.success:
            return ValidationResult(is_valid=False, issues=[f"Generation failed: {result.error}"])

        if result.data is None:
            return ValidationResult(is_valid=False, issues=["Generated data is None"])

        return ValidationResult(is_valid=True)

    def pre_generate_hook(self, context: GenerationContext) -> None:
        """
        Hook called before generation.

        Subclasses can override for preprocessing.

        Args:
            context: Generation context
        """

    def post_generate_hook(self, context: GenerationContext, result: GenerationResult[T]) -> None:
        """
        Hook called after generation.

        Subclasses can override for postprocessing.

        Args:
            context: Generation context
            result: Generation result
        """
