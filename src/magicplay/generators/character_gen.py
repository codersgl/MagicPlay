"""
Character Image Generator Module

Generates character anchor images for story consistency.
Phase 1 of the three-phase optimization architecture.
"""

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from magicplay.consistency.story_consistency import StoryConsistencyManager
from magicplay.schema.professional_workflow import (
    CharacterInfo,
    CharacterReference,
)
from magicplay.services.image_api import ImageService
from magicplay.utils.paths import DataManager


class CharacterImageGenerator:
    """
    Character image generator for Phase 1 consistency.

    Generates anchor images for characters to ensure visual consistency
    across all scenes and episodes.
    """

    def __init__(
        self,
        story_name: str,
        size: tuple = (1280, 720),
    ) -> None:
        """
        Initialize character image generator.

        Args:
            story_name: Name of the story
            size: Output image resolution (width, height)
        """
        self.story_name = story_name
        self.size = size

        # Ensure output directory exists
        self.output_dir = DataManager.get_character_anchors_path(story_name)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize image service
        self.image_service = ImageService()

        logger.info(f"CharacterImageGenerator initialized for story: {story_name}")

    def ensure_character_images(
        self,
        consistency_manager: StoryConsistencyManager,
    ) -> Dict[str, Path]:
        """
        Ensure all characters have anchor images.

        Generates missing images and returns a dict of character_name -> image_path.

        Args:
            consistency_manager: StoryConsistencyManager with loaded characters

        Returns:
            Dict mapping character names to their anchor image paths
        """
        generated_images: Dict[str, Path] = {}

        if not consistency_manager.characters:
            logger.warning("No characters found in consistency manager")
            return generated_images

        # Check existing images
        for char_name, char_anchor in consistency_manager.characters.items():
            if char_anchor.image_path and Path(char_anchor.image_path).exists():
                generated_images[char_name] = Path(char_anchor.image_path)
                logger.info(f"Character {char_name} already has anchor image: {char_anchor.image_path}")
            else:
                # Generate missing image
                logger.info(f"Generating anchor image for character: {char_name}")
                # Build description from visual_tags
                visual_tags_str = ", ".join(char_anchor.visual_tags) if char_anchor.visual_tags else ""
                character_description = (
                    f"{char_anchor.name}: {visual_tags_str}" if visual_tags_str else char_anchor.name
                )
                image_path = self.generate_character_image(
                    character_name=char_name,
                    character_description=character_description,
                )
                if image_path:
                    generated_images[char_name] = image_path
                    # Update consistency manager
                    consistency_manager.set_character_image_path(char_name, str(image_path))

        logger.info(f"Ensured {len(generated_images)} character anchor images")
        return generated_images

    def generate_character_image(
        self,
        character_name: str,
        character_description: str,
    ) -> Optional[Path]:
        """
        Generate an anchor image for a single character.

        Args:
            character_name: Name of the character
            character_description: Visual description of the character

        Returns:
            Path to generated image, or None if generation failed
        """
        # Create prompt for character image
        prompt = self._create_character_prompt(character_name, character_description)

        # Output path
        output_path = self.output_dir / f"{character_name}.jpg"

        # Generate and download image in one step
        try:
            result_path = self.image_service.generate_image_and_download(
                prompt=prompt,
                output_path=str(output_path),
                size=self.size,
                negative_prompt="low quality, blurry, distorted, deformed",
                n=1,
            )

            if result_path and Path(result_path).exists():
                logger.info(f"Character anchor image saved: {result_path}")
                return Path(result_path)
            else:
                logger.error(f"Failed to generate image for character: {character_name}")
                return None

        except Exception as e:
            logger.error(f"Error generating character image for {character_name}: {e}")
            return None

    def _create_character_prompt(self, character_name: str, description: str) -> str:
        """
        Create a detailed prompt for character image generation.

        Args:
            character_name: Name of the character
            description: Character description

        Returns:
            Formatted prompt string
        """
        # Create a detailed prompt for high-quality character portrait
        prompt = (
            f"Character portrait of {character_name}, {description}. "
            f"High-quality anime-style illustration, detailed facial features, "
            f"professional portrait, clear background, front-facing, "
            f"masterpiece, best quality, highly detailed"
        )
        return prompt

    def generate_character_batch(
        self,
        characters: List[CharacterInfo],
        consistency_manager: Optional[StoryConsistencyManager] = None,
    ) -> Dict[str, CharacterReference]:
        """
        Generate anchor images for multiple characters in batch.

        Args:
            characters: List of CharacterInfo objects
            consistency_manager: Optional StoryConsistencyManager for updates

        Returns:
            Dictionary mapping character name to CharacterReference objects
        """
        references = {}

        for char_info in characters:
            logger.info(f"Generating anchor image for character: {char_info.name}")

            # Build description from visual tags
            if char_info.visual_tags:
                description = ", ".join(char_info.visual_tags)
            elif char_info.appearance_description:
                description = char_info.appearance_description
            else:
                description = char_info.name

            # Use AI prompt if available, otherwise generate from description
            prompt = (
                char_info.ai_prompt
                if char_info.ai_prompt
                else self._create_character_prompt(char_info.name, description)
            )

            # Output path
            safe_name = self._sanitize_filename(char_info.name)
            output_path = self.output_dir / f"{safe_name}.jpg"

            # Check if already exists
            if output_path.exists():
                logger.info(f"Using existing anchor image for: {char_info.name}")
            else:
                try:
                    result_path = self.image_service.generate_image_and_download(
                        prompt=prompt,
                        output_path=str(output_path),
                        size=self.size,
                        negative_prompt="low quality, blurry, distorted, deformed, text, watermark",
                        n=1,
                    )

                    if result_path:
                        output_path = Path(result_path)
                    else:
                        logger.error(f"Failed to generate image for: {char_info.name}")
                        continue

                except Exception as e:
                    logger.error(f"Error generating image for {char_info.name}: {e}")
                    continue

            # Create reference object
            references[char_info.name] = CharacterReference(
                name=char_info.name,
                anchor_image_path=output_path,
                character_info=char_info,
            )

            # Update consistency manager if provided
            if consistency_manager and output_path.exists():
                consistency_manager.set_character_image_path(char_info.name, str(output_path))

        logger.info(f"Generated {len(references)} character anchor images")
        return references

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize character name for use as filename."""
        import re

        safe = re.sub(r"[^\w\s\-]", "_", name)
        safe = re.sub(r"[\s]+", "_", safe)
        return safe[:80]
