"""
MagicPlay Dependency Injection Container

Centralized dependency injection using dependency-injector library.
Provides wired dependencies for all application components.

Note: This is a work in progress. Some generators need to be refactored first.
"""

from dependency_injector import containers, providers

from magicplay.config import Settings
from magicplay.services.llm import LLMService
from magicplay.generators.script_gen import ScriptGenerator


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
    config = providers.Singleton(Settings)

    # Services - singleton instances
    llm_service = providers.Singleton(
        LLMService,
        config=config,
    )

    # Generators - factory instances (created per use)
    script_generator = providers.Factory(
        ScriptGenerator,
        config=config,
        llm_service=llm_service,
    )

    # Note: The following generators need to be refactored before adding:
    # - ImageGenerator (needs ImageService refactoring)
    # - VideoGenerator (needs VideoService refactoring)
    # - SceneConceptGenerator (needs rewrite - file corrupted)
    # - CharacterGenerator (needs rewrite)
    # - SceneSegmentGenerator (needs rewrite)


# Convenience function for getting container instances
def get_container() -> Container:
    """Get a new container instance."""
    return Container()
