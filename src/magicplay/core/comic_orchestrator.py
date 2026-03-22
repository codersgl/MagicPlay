"""
Comic Orchestrator Module

Orchestrates AI comic generation pipeline:
1. Load context (story bible, episode outline)
2. Ensure character anchor images
3. For each scene:
   - Generate/load scene script
   - Dynamic panel selection (LLM decides panel count)
   - Generate comic panels (WANX)
4. Output to panels/ directory
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

from magicplay.consistency.story_consistency import StoryConsistencyManager
from magicplay.core.orchestrator import Orchestrator  # Reuse some methods
from magicplay.generators.character_gen import CharacterImageGenerator
from magicplay.generators.comic_panel_gen import ComicPanelGenerator, PanelOutput
from magicplay.generators.dynamic_panel_selector import DynamicPanelSelector
from magicplay.generators.script_gen import ScriptGenerator
from magicplay.utils.paths import DataManager


class ComicOrchestrator:
    """
    Orchestrates comic generation pipeline.

    Reuses:
    - ScriptGenerator for scene scripts
    - CharacterImageGenerator for character anchors
    - ImageService for WANX image generation

    New:
    - DynamicPanelSelector for intelligent panel breakdown
    - ComicPanelGenerator for panel image generation
    """

    def __init__(
        self,
        story_name: str,
        episode_name: str,
        max_scenes: int = 5,
        genre: str = "",
        reference_story: str = "",
        comic_style: str = "anime",
    ):
        self.story_name = story_name
        self.episode_name = episode_name
        self.max_scenes = max_scenes
        self.genre = genre
        self.reference_story = reference_story
        self.comic_style = comic_style

        # Ensure directory structure
        DataManager.ensure_structure(story_name, episode_name)
        DataManager.ensure_comic_structure(story_name, episode_name)

        # Initialize generators
        self.scripts_dir = DataManager.get_generated_scripts_path(
            story_name, episode_name
        )
        self.scenes_dir = DataManager.get_scenes_path(story_name, episode_name)

        self.script_gen = ScriptGenerator(
            output_dir=self.scripts_dir,
            genre=self.genre,
            reference_story=self.reference_story,
        )
        self.character_gen = CharacterImageGenerator(story_name)
        self.panel_selector = DynamicPanelSelector()
        self.panel_gen = ComicPanelGenerator(
            story_name=story_name,
            episode_name=episode_name,
            style=comic_style,
        )

        # Consistency manager for character references
        self.consistency_manager: Optional[StoryConsistencyManager] = None

        logger.info(f"ComicOrchestrator initialized for {story_name}/{episode_name}")

    def run(self) -> List[List[PanelOutput]]:
        """
        Run the comic generation pipeline.

        Returns:
            List of scene results, each containing list of PanelOutput
        """
        # Load context
        story_ctx, episode_ctx = self.load_context()

        # Ensure character images (called for side effect)
        self._ensure_character_images()

        # Get scene scripts
        scenes = self._get_scene_scripts()

        # Generate comic panels for each scene
        all_results = []
        for i, scene_info in enumerate(scenes):
            if i >= self.max_scenes:
                logger.info(f"Reached max_scenes limit ({self.max_scenes})")
                break

            scene_name = scene_info["name"]
            scene_script = scene_info["script"]

            logger.info(f"Processing scene {i+1}: {scene_name}")

            # Dynamic panel selection
            characters_in_scene = self._get_characters_in_scene(scene_script)
            panels = self.panel_selector.analyze(
                scene_script=scene_script,
                characters=characters_in_scene,
                previous_context=scenes[i - 1]["script"] if i > 0 else "",
            )

            # Get character descriptions for reference
            char_descriptions = self._get_character_descriptions(characters_in_scene)

            # Generate panels
            scene_results = self.panel_gen.generate_scene_panels(
                panels=panels,
                character_descriptions=char_descriptions,
                scene_context=scene_script[:500],
            )

            all_results.append(scene_results)
            logger.info(f"Scene {i+1} complete: {len(scene_results)} panels generated")

        logger.info(f"Comic generation complete: {len(all_results)} scenes processed")
        return all_results

    def load_context(self) -> Tuple[str, str]:
        """
        Load or generate story context.

        Returns:
            Tuple of (story_context, episode_context)
        """
        # Reuse Orchestrator's load_context logic
        orchestrator = Orchestrator(
            story_name=self.story_name,
            episode_name=self.episode_name,
            genre=self.genre,
            reference_story=self.reference_story,
        )
        return orchestrator.load_context()  # type: ignore[no-any-return]

    def _ensure_character_images(self) -> Dict[str, Path]:
        """Ensure all characters have anchor images."""
        if self.consistency_manager is None:
            self.consistency_manager = StoryConsistencyManager(self.story_name)
            self.consistency_manager.load_from_story_bible()

        return self.character_gen.ensure_character_images(
            self.consistency_manager
        )

    def _get_scene_scripts(self) -> List[Dict[str, str]]:
        """Get all scene scripts for the episode."""
        scenes = []

        # Check for existing scene scripts
        scene_files = DataManager.get_scenes_prompts(self.story_name, self.episode_name)

        for scene_file in scene_files:
            scene_name = scene_file.stem
            scene_script = scene_file.read_text(encoding="utf-8")
            scenes.append({"name": scene_name, "script": scene_script})

        # If no scenes exist, generate them
        if not scenes:
            logger.info("No scene scripts found, generating from episode outline...")
            scenes = self._generate_scene_scripts()

        return scenes

    def _generate_scene_scripts(self) -> List[Dict[str, str]]:
        """Generate scene scripts from episode outline."""
        scenes = []
        _, episode_ctx = self.load_context()

        # Generate scene outlines
        for i in range(self.max_scenes):
            scene_name = f"scene_{i+1:03d}"
            try:
                scene_script = self.script_gen.generate_scene_script(
                    episode_outline=episode_ctx,
                    scene_number=i + 1,
                    previous_scene="",
                )

                # Save scene script
                scene_path = self.scenes_dir / f"{scene_name}.md"
                scene_path.write_text(scene_script, encoding="utf-8")

                scenes.append({"name": scene_name, "script": scene_script})
            except Exception as e:
                logger.error(f"Failed to generate scene {scene_name}: {e}")

        return scenes

    def _get_characters_in_scene(self, scene_script: str) -> List[str]:
        """Extract character names from scene script."""
        if self.consistency_manager is None:
            return []

        # Simple extraction - get characters whose names appear in script
        characters = []
        script_lower = scene_script.lower()
        for char_name in self.consistency_manager.characters.keys():
            if char_name.lower() in script_lower:
                characters.append(char_name)

        return (
            characters
            if characters
            else list(self.consistency_manager.characters.keys())[:2]
        )

    def _get_character_descriptions(self, characters: List[str]) -> Dict[str, str]:
        """Get character descriptions for prompt building."""
        descriptions: Dict[str, str] = {}

        if self.consistency_manager is None:
            return descriptions

        for char_name in characters:
            if char_name in self.consistency_manager.characters:
                char = self.consistency_manager.characters[char_name]
                visual_tags = (
                    ", ".join(char.visual_tags) if char.visual_tags else char.name
                )
                descriptions[char_name] = visual_tags

        return descriptions
