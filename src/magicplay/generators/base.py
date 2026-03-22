"""
MagicPlay Generator Base Classes

Abstract base classes and shared functionality for all generators.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from loguru import logger

from magicplay.config import Settings
from magicplay.ports.generators import (
    GenerationContext,
    GenerationResult,
    IGenerator,
    ValidationResult,
)

# Type variable for generic result type
T = TypeVar("T")


class BaseGenerator(IGenerator[T], ABC, Generic[T]):
    """
    Abstract base class for all MagicPlay generators.

    Provides common functionality:
    - Configuration access
    - Structured logging
    - Context validation
    - Result wrapping
    - Hook support

    Subclasses must implement:
    - generate() method
    - Optional: validate() for content-specific validation
    """

    name: str = "base_generator"
    description: str = "Base generator class"

    def __init__(self, config: Settings):
        """
        Initialize generator.

        Args:
            config: Application settings
        """
        self.config = config
        self.logger = logger

    @abstractmethod
    def generate(self, context: GenerationContext) -> GenerationResult[T]:
        """
        Generate content from the given context.

        Must be implemented by subclasses.

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

    def _wrap_success(
        self,
        data: T,
        context: GenerationContext,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GenerationResult[T]:
        """
        Wrap successful generation result.

        Args:
            data: Generated data
            context: Generation context
            metadata: Optional metadata

        Returns:
            GenerationResult with success=True
        """
        self.logger.info(f"{self.name}: Successfully generated {type(data).__name__}")
        return GenerationResult(
            success=True,
            data=data,
            metadata=metadata or {},
        )

    def _wrap_error(
        self,
        error: str,
        context: GenerationContext,
        warnings: Optional[List[str]] = None,
    ) -> GenerationResult[T]:
        """
        Wrap failed generation result.

        Args:
            error: Error message
            context: Generation context
            warnings: Optional warnings

        Returns:
            GenerationResult with success=False
        """
        self.logger.error(f"{self.name}: Generation failed - {error}")
        return GenerationResult(
            success=False,
            error=error,
            warnings=warnings or [],
        )

    def _wrap_partial(self, data: T, warnings: List[str], context: GenerationContext) -> GenerationResult[T]:
        """
        Wrap partial generation result (success with warnings).

        Args:
            data: Generated data
            warnings: List of warnings
            context: Generation context

        Returns:
            GenerationResult with success=True and warnings
        """
        self.logger.warning(f"{self.name}: Generated with warnings: {warnings}")
        return GenerationResult(
            success=True,
            data=data,
            warnings=warnings,
        )

    def pre_generate_hook(self, context: GenerationContext) -> None:
        """
        Hook called before generation.

        Subclasses can override for preprocessing.
        Default implementation logs the generation start.

        Args:
            context: Generation context
        """
        self.logger.info(
            f"{self.name}: Starting generation for {context.story_name}/{context.episode_name}/{context.scene_name}"
        )

    def post_generate_hook(self, context: GenerationContext, result: GenerationResult[T]) -> None:
        """
        Hook called after generation.

        Subclasses can override for postprocessing.
        Default implementation logs the result.

        Args:
            context: Generation context
            result: Generation result
        """
        if result.success:
            self.logger.info(f"{self.name}: Generation completed successfully")
        else:
            self.logger.error(f"{self.name}: Generation failed - {result.error}")

    def _validate_context(self, context: GenerationContext) -> Optional[str]:
        """
        Validate generation context before processing.

        Args:
            context: Generation context

        Returns:
            Error message if invalid, None if valid
        """
        if not context.story_name:
            return "story_name is required"

        if not context.episode_name:
            return "episode_name is required"

        return None

    def generate_with_context(
        self,
        story_name: str,
        episode_name: str,
        scene_name: str = "",
        **kwargs,
    ) -> GenerationResult[T]:
        """
        Convenience method to generate with simple parameters.

        Creates a GenerationContext from parameters and calls generate().

        Args:
            story_name: Story name
            episode_name: Episode name
            scene_name: Scene name (optional)
            **kwargs: Additional context parameters

        Returns:
            GenerationResult
        """
        context = GenerationContext(
            story_name=story_name,
            episode_name=episode_name,
            scene_name=scene_name,
            **kwargs,
        )
        return self.generate(context)
