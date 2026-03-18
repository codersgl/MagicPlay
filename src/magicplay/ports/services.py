"""
MagicPlay Service Interfaces

Abstract interfaces for external services (LLM, Image, Video APIs).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config import Settings


class ILLMService(ABC):
    """
    Interface for Large Language Model services.

    Implementations: DeepSeek, OpenAI, Anthropic, etc.
    """

    name: str = "base_llm"

    def __init__(self, config: Settings):
        self.config = config

    @abstractmethod
    def generate_content(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text content using LLM.

        Args:
            system_prompt: System instruction context
            user_prompt: User's request/prompt
            temperature: Creativity parameter (0.0-2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text content
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the service is operational.

        Returns:
            True if service is healthy, False otherwise
        """
        pass


class IImageService(ABC):
    """
    Interface for image generation services.

    Implementations: DashScope T2I, Stable Diffusion, DALL-E, etc.
    """

    name: str = "base_image"

    def __init__(self, config: Settings):
        self.config = config

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        output_path: Union[str, Path],
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        guidance_scale: float = 7.5,
        **kwargs
    ) -> Optional[Path]:
        """
        Generate an image from text prompt.

        Args:
            prompt: Text description of desired image
            output_path: Path to save generated image
            negative_prompt: Things to exclude from image
            width: Image width in pixels
            height: Image height in pixels
            steps: Number of diffusion steps
            guidance_scale: How closely to follow prompt
            **kwargs: Additional provider-specific parameters

        Returns:
            Path to generated image, or None on failure
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is operational."""
        pass


class IVideoService(ABC):
    """
    Interface for video generation services.

    Implementations: DashScope V2V/I2V, Runway, Pika, etc.
    """

    name: str = "base_video"

    def __init__(self, config: Settings):
        self.config = config

    @abstractmethod
    def generate_video(
        self,
        prompt: str,
        output_path: Union[str, Path],
        reference_image: Optional[Union[str, Path]] = None,
        duration: int = 5,
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> Optional[Path]:
        """
        Generate a video from prompt and optional reference image.

        Args:
            prompt: Text description of desired video
            output_path: Path to save generated video
            reference_image: Optional first frame reference
            duration: Video duration in seconds
            negative_prompt: Things to exclude from video
            **kwargs: Additional provider-specific parameters

        Returns:
            Path to generated video, or None on failure
        """
        pass

    @abstractmethod
    def extract_last_frame(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path]
    ) -> Optional[Path]:
        """
        Extract the last frame from a video.

        Args:
            video_path: Path to source video
            output_path: Path to save extracted frame

        Returns:
            Path to extracted frame, or None on failure
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is operational."""
        pass
