from dataclasses import dataclass
from typing import List, Optional
from loguru import logger

from magicplay.ports.services import ILLMService
from magicplay.services.llm import LLMService
from magicplay.config import Settings, get_settings


@dataclass
class PanelInfo:
    """Information about a single comic panel."""
    panel_number: int
    description: str
    dialogue: Optional[str] = None
    composition: str = "wide"  # close-up, wide, action, reaction, establishing
    emotion: str = "neutral"  # happy, sad, angry, surprised, neutral


class DynamicPanelSelector:
    """
    Analyzes scene scripts and determines optimal panel breakdown.
    Uses LLM to intelligently decide number of panels and their content.
    """

    name = "dynamic_panel_selector"
    description = "Dynamically selects panel breakdown for comic scenes"

    def __init__(
        self,
        config: Optional[Settings] = None,
        llm_service: Optional[ILLMService] = None,
        max_panels: int = 4,
    ):
        if config is None:
            config = get_settings()

        self.config = config
        self.llm = llm_service or LLMService(config)
        self.max_panels = max_panels

        # Load prompt template
        from pathlib import Path
        prompts_dir = Path(__file__).parent.parent / "prompts"
        try:
            self.prompt_template = (prompts_dir / "dynamic_panel_selector.md").read_text(encoding="utf-8")
        except FileNotFoundError:
            self.prompt_template = "Analyze the scene and determine panel breakdown."

    def analyze(
        self,
        scene_script: str,
        characters: List[str],
        previous_context: str = "",
    ) -> List[PanelInfo]:
        """
        Analyze scene script and return panel breakdown.

        Args:
            scene_script: The scene script text
            characters: List of character names in the scene
            previous_context: Context from previous scene (optional)

        Returns:
            List of PanelInfo objects describing each panel
        """
        # Build prompt
        character_list = ", ".join(characters) if characters else "No specific characters"
        prompt = self.prompt_template.format(
            scene_script=scene_script,
            character_list=character_list,
            previous_scene_context=previous_context or "None",
            max_panels=self.max_panels,
        )

        # Call LLM (use generate_content which takes system + user prompts)
        # For JSON response, instruct LLM clearly in prompt
        system_prompt = "You are a professional comic panel designer. Return ONLY valid JSON array."
        response = self.llm.generate_content(
            system_prompt=system_prompt,
            user_prompt=prompt,
        )

        # Parse JSON response
        try:
            import json
            panels_data = json.loads(response)
            panels = [
                PanelInfo(
                    panel_number=p["panel_number"],
                    description=p["description"],
                    dialogue=p.get("dialogue"),
                    composition=p.get("composition", "wide"),
                    emotion=p.get("emotion", "neutral"),
                )
                for p in panels_data
            ]
            logger.info(f"DynamicPanelSelector: Generated {len(panels)} panels")
            return panels
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse panel data: {e}")
            # Fallback: single panel
            return [PanelInfo(
                panel_number=1,
                description=scene_script[:200],
                dialogue=None,
                composition="wide",
                emotion="neutral",
            )]