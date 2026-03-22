from magicplay.core.comic_orchestrator import ComicOrchestrator


def test_comic_orchestrator_init():
    orchestrator = ComicOrchestrator(
        story_name="TestStory",
        episode_name="01",
        max_scenes=3,
    )
    assert orchestrator.story_name == "TestStory"
    assert orchestrator.episode_name == "01"
    assert orchestrator.max_scenes == 3
    assert orchestrator.comic_style == "anime"


def test_comic_orchestrator_custom_style():
    orchestrator = ComicOrchestrator(
        story_name="TestStory",
        episode_name="01",
        comic_style="comic",
    )
    assert orchestrator.comic_style == "comic"


def test_comic_orchestrator_has_generators():
    orchestrator = ComicOrchestrator(
        story_name="TestStory",
        episode_name="01",
    )
    assert orchestrator.script_gen is not None
    assert orchestrator.character_gen is not None
    assert orchestrator.panel_selector is not None
    assert orchestrator.panel_gen is not None
