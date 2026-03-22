"""
Scene Reference Generator for Professional Workflow Phase 2.

Generates dedicated scene reference images with 16:9 landscape aspect ratio
for the professional 6-stage workflow.
"""

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from magicplay.schema.professional_workflow import SceneInfo, SceneReference
from magicplay.services.image_api import ImageService
from magicplay.utils.paths import DataManager


class SceneReferenceGenerator:
    """
    Generates dedicated scene reference images (16:9 landscape) for Phase 2.

    These scene references are distinct from character anchors (2:3 portrait)
    and are used as visual references for video generation in the storyboard phase.
    """

    # Standard 16:9 aspect ratio
    SIZE_16_9 = (1280, 720)

    def __init__(
        self,
        story_name: str,
        episode_name: Optional[str] = None,
        size: tuple = SIZE_16_9,
    ) -> None:
        """
        Initialize scene reference generator.

        Args:
            story_name: Name of the story
            episode_name: Optional episode name (for per-episode references)
            size: Output image resolution (width, height), default 1280x720 (16:9)
        """
        self.story_name = story_name
        self.episode_name = episode_name
        self.size = size

        # Scene references are stored at story level (shared across episodes)
        self.output_dir = DataManager.get_scene_references_path(story_name)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize image service
        self.image_service = ImageService()

        logger.info(f"SceneReferenceGenerator initialized for {story_name}")

    def generate_scene_reference(
        self,
        scene_name: str,
        visual_prompt: str,
        setting: str = "",
        characters: Optional[List[str]] = None,
    ) -> Optional[Path]:
        """
        Generate a scene reference image for a scene.

        Args:
            scene_name: Name of the scene (used for filename)
            visual_prompt: Visual description prompt for the scene
            setting: Scene setting (e.g., "INT. COFFEE SHOP - DAY")
            characters: List of character names in this scene

        Returns:
            Path to generated scene reference image, or None on failure
        """
        # Sanitize scene name for filename
        safe_name = self._sanitize_filename(scene_name)
        output_path = self.output_dir / f"{safe_name}.jpg"

        # Check if already exists
        if output_path.exists():
            logger.info(f"Using existing scene reference: {output_path}")
            return output_path

        # Build enhanced prompt
        prompt = self._build_scene_prompt(visual_prompt, setting, characters)

        try:
            result_path = self.image_service.generate_image_and_download(
                prompt=prompt,
                output_path=str(output_path),
                size=self.size,
                negative_prompt=self._get_negative_prompt(),
                n=1,
            )

            if result_path and Path(result_path).exists():
                logger.info(f"Scene reference generated: {result_path}")
                return Path(result_path)
            else:
                logger.error(f"Failed to generate scene reference for: {scene_name}")
                return None

        except Exception as e:
            logger.error(f"Error generating scene reference for {scene_name}: {e}")
            return None

    def generate_scene_references_batch(
        self,
        scenes: List[SceneInfo],
    ) -> Dict[str, SceneReference]:
        """
        Generate scene reference images for multiple scenes.

        Args:
            scenes: List of SceneInfo objects

        Returns:
            Dictionary mapping scene_name to SceneReference objects
        """
        references = {}

        for scene in scenes:
            logger.info(f"Generating scene reference for: {scene.scene_name}")

            ref_path = self.generate_scene_reference(
                scene_name=scene.scene_name,
                visual_prompt=scene.ai_prompt,
                setting=scene.setting,
                characters=scene.characters,
            )

            if ref_path:
                references[scene.scene_name] = SceneReference(
                    scene_name=scene.scene_name,
                    reference_image_path=ref_path,
                    scene_info=scene,
                )

        logger.info(f"Generated {len(references)}/{len(scenes)} scene references")
        return references

    def get_scene_reference(self, scene_name: str) -> Optional[Path]:
        """
        Get path to existing scene reference image.

        Args:
            scene_name: Name of the scene

        Returns:
            Path to scene reference image, or None if not found
        """
        safe_name = self._sanitize_filename(scene_name)
        output_path = self.output_dir / f"{safe_name}.jpg"

        if output_path.exists():
            return output_path
        return None

    def _build_scene_prompt(
        self,
        visual_prompt: str,
        setting: str,
        characters: Optional[List[str]],
    ) -> str:
        """
        Build enhanced scene prompt from components.

        Args:
            visual_prompt: Base visual prompt
            setting: Scene setting string
            characters: Character names in scene

        Returns:
            Enhanced prompt string
        """
        prompt_parts = []

        # Add setting context if provided
        if setting:
            # Parse setting components
            parts = setting.split(" - ")
            location = parts[0] if parts else setting
            time_of_day = parts[1] if len(parts) > 1 else "day"
            prompt_parts.append(f"Setting: {location}, {time_of_day}")

        # Add visual prompt
        prompt_parts.append(visual_prompt)

        # Add characters if provided
        if characters:
            char_str = ", ".join(characters[:3])  # Max 3 characters
            prompt_parts.append(f"Characters present: {char_str}")

        # Add style requirements
        prompt_parts.append(
            "anime style background, cinematic composition, wide establishing shot, atmospheric lighting"
        )

        return " | ".join(prompt_parts)

    def _get_negative_prompt(self) -> str:
        """Get negative prompt for quality control."""
        return (
            "low quality, blurry, text, watermark, deformed, "
            "bad anatomy, extra limbs, floating objects, "
            "inconsistent lighting, color shifting, photographic, realistic"
        )

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """
        Sanitize scene name for use as filename.

        Args:
            name: Original scene name

        Returns:
            Sanitized filename-safe string
        """
        import re

        # Replace common filename-unsafe characters
        safe = re.sub(r"[^\w\s\-]", "_", name)
        safe = re.sub(r"[\s]+", "_", safe)
        safe = re.sub(r"_+", "_", safe)
        return safe[:100]  # Limit length
