from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

from magicplay.config import Settings, get_settings
from magicplay.services.image_api import ImageService
from magicplay.utils.paths import DataManager

from .dynamic_panel_selector import PanelInfo


@dataclass
class PanelOutput:
    """Output from comic panel generation."""

    panel_number: int
    image_path: Path
    description: str
    dialogue: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class ComicPanelGenerator:
    """
    Generates comic panel images using WANX text-to-image API.
    Supports text-in-image for dialogue rendering.
    """

    name = "comic_panel_generator"
    description = "Generates comic panel images with embedded text"

    def __init__(
        self,
        story_name: str,
        episode_name: str,
        config: Optional[Settings] = None,
        style: str = "anime",
    ):
        if config is None:
            config = get_settings()

        self.story_name = story_name
        self.episode_name = episode_name
        self.config = config
        self.style = style

        # Output directory
        self.output_dir = DataManager.get_comic_panels_path(story_name, episode_name)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Image service
        self.image_service = ImageService()

        # Load prompt template
        from pathlib import Path

        prompts_dir = Path(__file__).parent.parent / "prompts"
        try:
            self.prompt_template = (prompts_dir / "comic_panel.md").read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            self.prompt_template = "Create a comic panel: {panel_description}"

    def generate_panel(
        self,
        panel_info: PanelInfo,
        character_descriptions: Dict[str, str],
        scene_context: str = "",
    ) -> PanelOutput:
        """
        Generate a single comic panel image.

        Args:
            panel_info: Panel information from DynamicPanelSelector
            character_descriptions: Dict mapping character name to description
            scene_context: Additional scene context

        Returns:
            PanelOutput with generated image path
        """
        # Build character description string
        char_desc_str = (
            "\n".join(
                f"- {name}: {desc}" for name, desc in character_descriptions.items()
            )
            if character_descriptions
            else "No specific characters"
        )

        # Build dialogue text if present
        dialogue_section = (
            f"Dialogue/Text: {panel_info.dialogue}"
            if panel_info.dialogue
            else "No dialogue"
        )

        # Create prompt
        prompt = self._build_prompt(
            panel_info=panel_info,
            char_desc_str=char_desc_str,
            dialogue_section=dialogue_section,
            scene_context=scene_context,
        )

        # Output path
        scene_dir = self.output_dir / f"scene_{panel_info.panel_number:03d}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        output_path = scene_dir / f"panel_{panel_info.panel_number:03d}.png"

        try:
            # Generate and download image
            # Parse "WIDTH*HEIGHT" string to tuple
            size = self._parse_resolution(self.config.comic_image_resolution)
            result_path = self.image_service.generate_image_and_download(
                prompt=prompt,
                output_path=str(output_path),
                size=size,
                negative_prompt="low quality, blurry, distorted, deformed, bad anatomy, watermark",
                n=1,
            )

            if result_path and Path(result_path).exists():
                logger.info(f"Comic panel saved: {result_path}")
                return PanelOutput(
                    panel_number=panel_info.panel_number,
                    image_path=Path(result_path),
                    description=panel_info.description,
                    dialogue=panel_info.dialogue,
                    success=True,
                )
            else:
                return PanelOutput(
                    panel_number=panel_info.panel_number,
                    image_path=output_path,
                    description=panel_info.description,
                    dialogue=panel_info.dialogue,
                    success=False,
                    error="Image generation failed",
                )

        except Exception as e:
            logger.error(f"Error generating panel {panel_info.panel_number}: {e}")
            return PanelOutput(
                panel_number=panel_info.panel_number,
                image_path=output_path,
                description=panel_info.description,
                dialogue=panel_info.dialogue,
                success=False,
                error=str(e),
            )

    def generate_scene_panels(
        self,
        panels: List[PanelInfo],
        character_descriptions: Dict[str, str],
        scene_context: str = "",
    ) -> List[PanelOutput]:
        """
        Generate all panels for a scene.

        Args:
            panels: List of PanelInfo from DynamicPanelSelector
            character_descriptions: Character descriptions for consistency
            scene_context: Scene context for prompt building

        Returns:
            List of PanelOutput objects
        """
        results = []
        for panel in panels:
            output = self.generate_panel(panel, character_descriptions, scene_context)
            results.append(output)
            if not output.success:
                logger.warning(f"Panel {panel.panel_number} failed: {output.error}")

        logger.info(f"Generated {len(results)} panels for scene")
        return results

    @staticmethod
    def _parse_resolution(resolution_str: str) -> Tuple[int, int]:
        """Parse 'WIDTH*HEIGHT' string to tuple."""
        try:
            width, height = resolution_str.split("*")
            return (int(width), int(height))
        except (ValueError, AttributeError):
            return (1024, 1024)  # Default fallback

    def _build_prompt(
        self,
        panel_info: PanelInfo,
        char_desc_str: str,
        dialogue_section: str,
        scene_context: str,
    ) -> str:
        """Build the generation prompt for a panel."""
        # Map emotion to style hints
        emotion_styles = {
            "happy": "bright lighting, warm colors, cheerful atmosphere",
            "sad": "dim lighting, cool colors, melancholic atmosphere",
            "angry": "harsh lighting, red accents, tension",
            "surprised": "dynamic composition, wide eyes, exclamation",
            "neutral": "balanced lighting, natural colors",
        }
        emotion_style = emotion_styles.get(panel_info.emotion, "")

        # Map composition to framing hints
        composition_hints = {
            "close-up": "Head and shoulders framing, detailed facial expression",
            "wide": "Full body or scene view, establishing shot",
            "action": "Dynamic angle, motion lines, dynamic pose",
            "reaction": "Focus on character's response, secondary subject blurred",
            "establishing": "Wide shot, environmental context, setting detail",
        }
        composition_hint = composition_hints.get(panel_info.composition, "")

        prompt = f"""Comic panel: {panel_info.description}

Composition: {composition_hint}
Emotion/Atmosphere: {emotion_style}

Characters:
{char_desc_str}

{dialogue_section}

Style: {self.style} manga/comic style
- High quality illustration
- Clean linework
- Professional comic art style
- Text naturally integrated if dialogue present
"""
        return prompt
