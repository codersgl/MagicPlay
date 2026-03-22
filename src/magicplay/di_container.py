"""
MagicPlay Dependency Injection Container

Centralized dependency injection using dependency-injector library.
Provides wired dependencies for all application components.
"""

from dependency_injector import containers, providers

from magicplay.analyzer.timeline_analyzer import TimelineAnalyzer
from magicplay.config import Settings, get_settings
from magicplay.generators.character_gen import CharacterImageGenerator
from magicplay.generators.comic_panel_gen import ComicPanelGenerator
from magicplay.generators.dynamic_panel_selector import DynamicPanelSelector
from magicplay.generators.scene_concept_gen import SceneConceptGenerator
from magicplay.generators.scene_segment_gen import SceneSegmentGenerator
from magicplay.generators.script_gen import ScriptGenerator
from magicplay.generators.video_gen import VideoGenerator
from magicplay.services.image_api import ImageService
from magicplay.services.jimeng_video_api import JimengVideoService
from magicplay.services.llm import LLMService
from magicplay.services.video_api import VideoService


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for MagicPlay.

    Usage:
        container = Container()
        script_gen = container.script_generator()

    Or with dependency injection:
        @container.inject
        def my_func(script_gen: ScriptGenerator):
            ...
    """

    # Configuration
    config = providers.Singleton(get_settings)

    # Services - singleton instances
    llm_service = providers.Singleton(
        LLMService,
        config=config,
    )

    image_service = providers.Factory(
        ImageService,
        config=config,
    )

    video_service = providers.Factory(
        VideoService,
    )

    jimeng_video_service = providers.Factory(
        JimengVideoService,
        config=config,
    )

    # Generators - factory instances (created per use)
    script_generator = providers.Factory(
        ScriptGenerator,
        config=config,
        llm_service=llm_service,
    )

    video_generator = providers.Factory(
        VideoGenerator,
    )

    def character_image_generator(self, story_name: str):
        """Create a CharacterImageGenerator for a specific story."""
        return CharacterImageGenerator(story_name=story_name)

    def scene_concept_generator(self, story_name: str, episode_name: str):
        """Create a SceneConceptGenerator for a specific story/episode."""
        return SceneConceptGenerator(
            story_name=story_name,
            episode_name=episode_name,
        )

    def scene_segment_generator(self, story_name: str, episode_name: str):
        """Create a SceneSegmentGenerator for a specific story/episode."""
        return SceneSegmentGenerator(
            story_name=story_name,
            episode_name=episode_name,
        )

    # Comic Generators
    def comic_panel_generator(self, story_name: str, episode_name: str):
        """Create a ComicPanelGenerator for a specific story/episode."""
        return ComicPanelGenerator(
            story_name=story_name,
            episode_name=episode_name,
        )

    def dynamic_panel_selector(self):
        """Create a DynamicPanelSelector."""
        return DynamicPanelSelector()

    # Analyzers - factory instances (created per use)
    timeline_analyzer = providers.Factory(
        TimelineAnalyzer,
        llm_service=llm_service,
    )


# Convenience function for getting container instances
def get_container() -> Container:
    """Get a new container instance."""
    return Container()
