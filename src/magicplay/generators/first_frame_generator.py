"""
First Frame Generator for Professional Workflow Phase 4.

Generates first frame images using image-to-image (I2I) with references
for the professional 6-stage workflow.
"""

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from magicplay.schema.professional_workflow import (
    CharacterReference,
    SceneReference,
    Storyboard,
    StoryboardFrame,
)
from magicplay.services.image_api import ImageService
from magicplay.utils.paths import DataManager


class FirstFrameGenerator:
    """
    Generates first frame images using I2I with reference images.

    Phase 4 takes storyboard frames and generates the actual first frame images
    using the scene reference and character references as input to ensure
    visual consistency.
    """

    def __init__(
        self,
        story_name: str,
        episode_name: str,
    ) -> None:
        """
        Initialize first frame generator.

        Args:
            story_name: Name of the story
            episode_name: Name of the episode
        """
        self.story_name = story_name
        self.episode_name = episode_name

        # Output directory: storyboard/scene_name/
        self.output_dir = DataManager.get_storyboard_path(story_name, episode_name)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize image service
        self.image_service = ImageService()

        logger.info(f"FirstFrameGenerator initialized for {story_name}/{episode_name}")

    def generate_first_frame(
        self,
        storyboard_frame: StoryboardFrame,
        scene_reference: SceneReference,
        character_images: Dict[str, CharacterReference],
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Generate first frame image for a storyboard frame.

        Args:
            storyboard_frame: StoryboardFrame with prompt and timing info
            scene_reference: SceneReference with scene image
            character_images: Dict of character name -> CharacterReference
            output_path: Optional output path (generated if not provided)

        Returns:
            Path to generated first frame image, or None on failure
        """
        # Build output path if not provided
        if output_path is None:
            scene_dir = self.output_dir / self._sanitize_filename(
                storyboard_frame.frame_index
            )
            scene_dir.mkdir(parents=True, exist_ok=True)
            output_path = (
                scene_dir / f"first_frame_{storyboard_frame.frame_index:02d}.jpg"
            )

        # Collect reference images
        ref_images = []

        # Add scene reference
        if scene_reference.reference_image_path.exists():
            ref_images.append(str(scene_reference.reference_image_path))

        # Add character references for this frame
        for char_name in storyboard_frame.characters:
            if char_name in character_images:
                char_ref = character_images[char_name]
                if char_ref.anchor_image_path.exists():
                    ref_images.append(str(char_ref.anchor_image_path))

        # Build prompt
        prompt = self._build_i2i_prompt(storyboard_frame, character_images)

        try:
            if ref_images:
                # Use I2I with references
                result_path = self.image_service.generate_image_i2i(
                    prompt=prompt,
                    input_images=ref_images,
                    output_path=str(output_path),
                    size=(1280, 720),
                )
            else:
                # Fall back to T2I without references
                result_path = self.image_service.generate_image_and_download(
                    prompt=prompt,
                    output_path=str(output_path),
                    size=(1280, 720),
                )

            if result_path and Path(result_path).exists():
                logger.info(f"First frame generated: {result_path}")
                return Path(result_path)
            else:
                logger.error("First frame generation failed")
                return None

        except Exception as e:
            logger.error(f"Error generating first frame: {e}")
            return None

    def generate_storyboard_first_frames(
        self,
        storyboard: Storyboard,
        scene_reference: SceneReference,
        character_images: Dict[str, CharacterReference],
    ) -> List[Path]:
        """
        Generate first frame images for all frames in a storyboard.

        Args:
            storyboard: Storyboard with all frames
            scene_reference: SceneReference with scene image
            character_images: Dict of character name -> CharacterReference

        Returns:
            List of paths to generated first frame images
        """
        generated_frames = []
        scene_dir = self.output_dir / self._sanitize_filename(storyboard.scene_name)
        scene_dir.mkdir(parents=True, exist_ok=True)

        for frame in storyboard.frames:
            output_path = scene_dir / f"first_frame_{frame.frame_index:02d}.jpg"

            logger.info(
                f"Generating first frame {frame.frame_index + 1}/{len(storyboard.frames)} "
                f"for scene: {storyboard.scene_name}"
            )

            result = self.generate_first_frame(
                storyboard_frame=frame,
                scene_reference=scene_reference,
                character_images=character_images,
                output_path=output_path,
            )

            if result:
                frame.first_frame_path = result
                generated_frames.append(result)

        logger.info(
            f"Generated {len(generated_frames)}/{len(storyboard.frames)} first frames"
        )
        return generated_frames

    def _build_i2i_prompt(
        self,
        storyboard_frame: StoryboardFrame,
        character_images: Dict[str, CharacterReference],
    ) -> str:
        """
        Build prompt for I2I first frame generation.

        Args:
            storyboard_frame: StoryboardFrame with prompt info
            character_images: Available character references

        Returns:
            Enhanced prompt string
        """
        prompt_parts = []

        # Add first frame prompt from storyboard
        if storyboard_frame.first_frame_prompt:
            prompt_parts.append(storyboard_frame.first_frame_prompt)

        # Add character context
        frame_chars = storyboard_frame.characters
        if frame_chars:
            char_refs = [
                character_images.get(name)
                for name in frame_chars
                if name in character_images
            ]
            if char_refs:
                char_names = [ref.name for ref in char_refs if ref]
                prompt_parts.append(f"Characters: {', '.join(char_names)}")

        # Add quality/style requirements
        prompt_parts.append(
            "anime style, high quality, detailed, sharp focus, "
            "cinematic lighting, masterpiece"
        )

        return " | ".join(prompt_parts)

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize name for use as directory name."""
        import re

        safe = re.sub(r"[^\w\s\-]", "_", str(name))
        safe = re.sub(r"[\s]+", "_", safe)
        return safe[:100]
