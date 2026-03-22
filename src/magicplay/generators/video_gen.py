"""
Video Generator Module

Generates videos using various video generation APIs.
Supports multiple providers: DashScope (qwen) and Jimeng (即梦).
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from magicplay.config import get_settings
from magicplay.services.jimeng_video_api import JimengVideoService
from magicplay.services.video_api import VideoService
from magicplay.utils.media import MediaUtils

logger = logging.getLogger(__name__)


class VideoGenerator:
    """
    Video generation orchestrator.

    Supports multiple video generation providers:
    - "qwen" (default): DashScope wan2.6 video models
    - "jimeng": Jimeng (即梦) AI video models

    Phase 2: Unified video generation mode ensures consistency
    by always using image-to-video (i2v) with concept images.
    """

    SUPPORTED_PROVIDERS = ["qwen", "jimeng"]

    def __init__(
        self,
        api_provider: Optional[str] = None,
        size: Tuple[int, int] = (1280, 720),
        duration: int = 15,
        unified_mode: bool = True,  # Phase 2: Unified video generation mode
    ) -> None:
        """
        Initialize video generator.

        Args:
            api_provider: Video generation provider ("qwen" or "jimeng").
                          If None, uses default_video_provider from settings.
            size: Output video resolution (width, height)
            duration: Default video duration in seconds
            unified_mode: If True, always use i2v with reference images
        """
        # Get default provider from settings if not specified
        if api_provider is None:
            settings = get_settings()
            api_provider = settings.default_video_provider
            logger.info(f"No provider specified, using default: {api_provider}")

        if api_provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {api_provider}. "
                f"Supported: {self.SUPPORTED_PROVIDERS}"
            )

        self.api_provider = api_provider
        self.size = size
        self.duration = duration
        self.unified_mode = unified_mode

        # Initialize the appropriate service
        if api_provider == "jimeng":
            settings = get_settings()
            self.service = JimengVideoService(config=settings)
            logger.info("Using Jimeng AI video service")
        else:
            self.service = VideoService(api_provider=api_provider)
            logger.info(f"Using DashScope video service (provider: {api_provider})")

        # Map size to aspect ratio for Jimeng
        self._aspect_ratio = self._size_to_aspect_ratio(size)

    def _size_to_aspect_ratio(self, size: Tuple[int, int]) -> str:
        """Convert size tuple to aspect ratio string for Kling API."""
        width, height = size
        ratio = width / height

        if abs(ratio - 16/9) < 0.1:
            return "16:9"
        elif abs(ratio - 9/16) < 0.1:
            return "9:16"
        elif abs(ratio - 1) < 0.1:
            return "1:1"
        elif abs(ratio - 4/3) < 0.1:
            return "4:3"
        elif abs(ratio - 3/4) < 0.1:
            return "3:4"
        elif abs(ratio - 3/2) < 0.1:
            return "3:2"
        elif abs(ratio - 2/3) < 0.1:
            return "2:3"
        elif abs(ratio - 21/9) < 0.1:
            return "21:9"
        else:
            # Default to 16:9
            return "16:9"

    def generate_video(
        self,
        visual_prompt: str,
        output_path: Union[str, Path],
        ref_img_path: Optional[Union[str, Path]] = None,
        duration: Optional[int] = None,
        force_unified_mode: Optional[bool] = None,
        api_provider: Optional[str] = None,
    ) -> Path:
        """
        Generate a video from a visual prompt string.

        Phase 2: Unified video generation mode:
        - Always use image-to-video (i2v) model when a reference image is provided
        - Even for first scene, generate concept image first, then use i2v
        - This ensures consistency across all video generation

        Args:
            visual_prompt: Text description of the video content
            output_path: Path to save the generated video
            ref_img_path: Optional reference image for i2v generation
            duration: Optional custom duration (overrides instance default)
            force_unified_mode: Force unified mode on/off
            api_provider: Override provider for this call ("qwen" or "jimeng")

        Returns:
            Path to the generated video
        """
        output_path = Path(output_path)
        ref_path_obj = Path(ref_img_path) if ref_img_path else None

        # Determine effective provider (runtime override or instance default)
        effective_provider = api_provider if api_provider else self.api_provider

        # Validate provider if overridden
        if api_provider and api_provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {api_provider}. "
                f"Supported: {self.SUPPORTED_PROVIDERS}"
            )

        # Determine if we should use unified mode
        use_unified = (
            force_unified_mode if force_unified_mode is not None else self.unified_mode
        )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Generating video to {output_path}...")
        print(f"Provider: {effective_provider}")

        # Unified mode logic
        if use_unified:
            if ref_path_obj:
                print(
                    f"Unified mode: Using reference image for image-to-video generation: {ref_path_obj}"
                )
            else:
                print(
                    f"Unified mode: No reference image provided. "
                    f"This is expected for the first scene - concept image should be generated separately."
                )
        else:
            if ref_path_obj:
                print(f"Legacy mode: Using reference image: {ref_path_obj}")

        # Use provided duration or fallback to instance default
        video_duration = duration if duration is not None else self.duration
        print(f"Video duration: {video_duration} seconds")

        try:
            # Determine which service to use (handle runtime provider switching)
            if effective_provider != self.api_provider:
                # Need to create a new service for the different provider
                if effective_provider == "jimeng":
                    settings = get_settings()
                    service = JimengVideoService(config=settings)
                else:
                    service = VideoService(api_provider=effective_provider)
            else:
                service = self.service

            if effective_provider == "jimeng":
                # Use Jimeng service
                result = service.generate_video(
                    prompt=visual_prompt,
                    output_path=output_path,
                    reference_image=ref_path_obj if ref_path_obj else None,
                    duration=video_duration,
                    aspect_ratio=self._aspect_ratio,
                )

                if result and result.exists():
                    print(f"Video saved to: {result}")
                    return result
                else:
                    raise RuntimeError("Jimeng video generation returned no result")

            else:
                # Use DashScope service (qwen)
                video_url = service.generate_video_url(
                    prompt=visual_prompt,
                    size=self.size,
                    duration=video_duration,
                    ref_img_path=str(ref_path_obj) if ref_path_obj else None,
                )

                if MediaUtils.download_video(video_url, output_path):
                    print(f"Video saved to: {output_path}")
                    return output_path
                else:
                    raise RuntimeError("Failed to download generated video")

        except Exception as e:
            raise RuntimeError(f"Video generation failed: {e}")

    def generate_video_unified(
        self,
        visual_prompt: str,
        output_path: Union[str, Path],
        concept_image_path: Union[str, Path],
        duration: Optional[int] = None,
    ) -> Path:
        """
        Unified video generation method that explicitly requires a concept image.
        This is the recommended method for Phase 2 optimization.

        Args:
            visual_prompt: Visual prompt for the scene
            output_path: Path to save the generated video
            concept_image_path: Path to the concept image (first frame)
            duration: Optional custom duration for the video

        Returns:
            Path to the generated video
        """
        concept_path = Path(concept_image_path)
        if not concept_path.exists():
            raise FileNotFoundError(f"Concept image not found: {concept_image_path}")

        print(
            f"Unified video generation: Using concept image as reference: {concept_path}"
        )

        return self.generate_video(
            visual_prompt=visual_prompt,
            output_path=output_path,
            ref_img_path=concept_image_path,
            duration=duration,
            force_unified_mode=True,
        )
