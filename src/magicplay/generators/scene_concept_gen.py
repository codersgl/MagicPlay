"""
Scene Concept Generator Module

Generates scene concept images for Phase 2 of the optimization pipeline.
Ensures consistent visual quality across all video generation.
"""

import re
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from magicplay.services.image_api import ImageService
from magicplay.utils.paths import DataManager


class SceneConceptGenerator:
    """
    Scene concept image generator for Phase 2 unified generation.

    Generates concept images that serve as reference for video generation,
    ensuring visual consistency across all scenes.
    """

    def __init__(
        self,
        story_name: str,
        episode_name: str,
        size: tuple = (1280, 720),
    ) -> None:
        """
        Initialize scene concept generator.

        Args:
            story_name: Name of the story
            episode_name: Name of the episode
            size: Output image resolution (width, height)
        """
        self.story_name = story_name
        self.episode_name = episode_name
        self.size = size

        # Ensure output directory exists
        self.output_dir = DataManager.get_scene_concepts_path(story_name, episode_name)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize image service
        self.image_service = ImageService()

        logger.info(f"SceneConceptGenerator initialized for {story_name}/{episode_name}")

    def get_or_create_scene_concept_image(
        self,
        scene_name: str,
        visual_prompt: str,
    ) -> Optional[Path]:
        """
        Get existing scene concept image or create a new one.

        Args:
            scene_name: Name of the scene
            visual_prompt: Visual description for the scene

        Returns:
            Path to scene concept image, or None if generation failed
        """
        # Check if image already exists
        concept_image_path = self.output_dir / f"{scene_name}.jpg"

        if concept_image_path.exists():
            logger.info(f"Using existing concept image for scene: {scene_name}")
            return concept_image_path

        # Generate new concept image
        logger.info(f"Generating concept image for scene: {scene_name}")
        return self.generate_scene_concept_image(scene_name, visual_prompt)

    def generate_scene_concept_image(
        self,
        scene_name: str,
        visual_prompt: str,
    ) -> Optional[Path]:
        """
        Generate a concept image for a scene.

        Args:
            scene_name: Name of the scene
            visual_prompt: Visual description for the scene

        Returns:
            Path to generated image, or None if generation failed
        """
        # Create enhanced prompt for scene concept
        prompt = self._create_scene_prompt(visual_prompt)

        # Output path
        output_path = self.output_dir / f"{scene_name}.jpg"

        # Generate and download image
        try:
            result_path = self.image_service.generate_image_and_download(
                prompt=prompt,
                output_path=str(output_path),
                size=self.size,
                negative_prompt="low quality, blurry, text, watermark, deformed",
                n=1,
            )

            if result_path and Path(result_path).exists():
                logger.info(f"Scene concept image saved: {result_path}")
                return Path(result_path)
            else:
                logger.error(f"Failed to generate concept image for scene: {scene_name}")
                return None

        except Exception as e:
            logger.error(f"Error generating concept image for {scene_name}: {e}")
            return None

    def ensure_scene_concept_image(
        self,
        scene_name: str,
        scene_script: str,
        use_previous_scene: bool = False,
        previous_scene_image: Optional[str] = None,
        story_context: str = "",
        character_images: Optional[dict] = None,
        character_profiles: Optional[Dict[str, str]] = None,
        visual_style: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Ensure a scene concept image exists, generating if necessary.

        This is the main entry point used by the Orchestrator.

        Args:
            scene_name: Name of the scene
            scene_script: Script content for the scene
            use_previous_scene: Whether to use previous scene as reference
            previous_scene_image: Path to valid previous concept image (.jpg/.png)
            story_context: Story context (used to extract cinematic style guide)
            character_images: Dict of character name -> image path (unused, kept for compat)
            character_profiles: Dict of character name -> Visual Tags string
            visual_style: Explicit cinematic visual style for the entire story

        Returns:
            Path to scene concept image, or None if generation failed
        """
        # Check if image already exists
        concept_image_path = self.output_dir / f"{scene_name}.jpg"

        if concept_image_path.exists():
            logger.info(f"Using existing concept image for scene: {scene_name}")
            return concept_image_path

        # Build visual prompt from scene script (correctly extracts VISUAL KEY block)
        visual_prompt = self._extract_visual_prompt(scene_script)

        # Augment with character Visual Tags for consistency anchoring
        if character_profiles:
            char_tags_str = "; ".join(character_profiles.values())
            visual_prompt = f"{visual_prompt}\n\n角色 Visual Tags (严格遵守): {char_tags_str}"

        # Prepend cinematic style guide extracted from story context
        style_prefix = ""
        if visual_style:
            style_prefix = visual_style
        elif story_context:
            style_prefix = self._extract_style_guide(story_context)

        if style_prefix:
            visual_prompt = f"{style_prefix}\n\n{visual_prompt}"

        # Add visual continuity instruction if a previous concept image is available
        if previous_scene_image:
            prev_path = Path(previous_scene_image)
            if prev_path.exists() and prev_path.suffix.lower() in (
                ".jpg",
                ".jpeg",
                ".png",
            ):
                visual_prompt = f"延续上一场景的视觉风格（色调、光影、空间布局保持一致）。\n{visual_prompt}"

        # Generate new concept image
        logger.info(f"Generating concept image for scene: {scene_name}")
        return self.generate_scene_concept_image(scene_name, visual_prompt)

    def _extract_visual_prompt(self, scene_script: str) -> str:
        """
        Extract visual description from scene script using the VISUAL KEY block.

        Uses the same 3-strategy regex approach as _extract_visual_key_from_script
        in script_gen.py to consistently locate the ```visual_key``` code block.

        Args:
            scene_script: Scene script content

        Returns:
            Visual description string extracted from the VISUAL KEY block,
            or a plain-text fallback from the first non-heading lines.
        """
        # Strategy 1: ```visual_key ... ``` fenced code block (preferred)
        fenced_match = re.search(
            r"```visual_key\s*\n(.*?)\n```",
            scene_script,
            re.DOTALL | re.IGNORECASE,
        )
        if fenced_match:
            return fenced_match.group(1).strip()

        # Strategy 2: Generic fenced block after a VISUAL KEY header
        header_fenced_match = re.search(
            r"##[#]?\s*(?:\d+\.\s*)?VISUAL KEY[^\n]*\n+```[^\n]*\n(.*?)\n```",
            scene_script,
            re.DOTALL | re.IGNORECASE,
        )
        if header_fenced_match:
            return header_fenced_match.group(1).strip()

        # Strategy 3: Plain text under VISUAL KEY header up to next section
        plain_match = re.search(
            r"##[#]?\s*(?:\d+\.\s*)?VISUAL KEY[^\n]*\n+(.*?)(?=\n##[#]?\s|\Z)",
            scene_script,
            re.DOTALL | re.IGNORECASE,
        )
        if plain_match:
            text = plain_match.group(1).strip()
            if text:
                return text

        # Fallback: first meaningful non-heading lines of the script
        lines = scene_script.strip().split("\n")
        visual_lines = [line.strip() for line in lines[:10] if line.strip() and not line.lstrip().startswith("#")]
        return " ".join(visual_lines) if visual_lines else scene_script[:200]

    def _extract_style_guide(self, story_context: str) -> str:
        """
        Extract the Cinematic Style Guide section from the story bible.

        Args:
            story_context: Full story bible content

        Returns:
            Style guide text (up to 300 chars), or empty string if not found.
        """
        match = re.search(
            r"##[#]?\s*(?:\d+\.\s*)?Cinematic Style Guide[^\n]*\n+(.*?)(?=\n##[#]?\s|\Z)",
            story_context,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()[:300]
        return ""

    def _create_scene_prompt(self, visual_prompt: str) -> str:
        """
        Create an enhanced prompt for scene concept image generation.

        Args:
            visual_prompt: Original visual prompt

        Returns:
            Enhanced prompt string
        """
        # Prepend quality tags only if not already present
        quality_tags = "Anime style, cel shaded, vibrant colors, clean lineart, soft shading, masterpiece, best quality"
        if "anime" not in visual_prompt.lower():
            enhanced_prompt = f"{quality_tags}. {visual_prompt}"
        else:
            enhanced_prompt = visual_prompt
        return enhanced_prompt
