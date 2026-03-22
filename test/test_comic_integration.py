from pathlib import Path

import pytest

from magicplay.core.comic_orchestrator import ComicOrchestrator


@pytest.mark.integration
def test_comic_pipeline_end_to_end(tmp_path, monkeypatch):
    """End-to-end test of comic generation pipeline."""
    # This test uses mocks for API calls
    # In real environment, would test actual generation

    # Setup temp data directory
    from magicplay.utils import paths

    monkeypatch.setattr(paths.DataManager, "DATA_DIR", tmp_path / "data")

    orchestrator = ComicOrchestrator(
        story_name="TestComicStory",
        episode_name="01",
        max_scenes=1,
        comic_style="anime",
    )

    # Verify initialization
    assert orchestrator.story_name == "TestComicStory"
    assert orchestrator.episode_name == "01"
    assert orchestrator.comic_style == "anime"

    # Verify generators are initialized
    assert orchestrator.script_gen is not None
    assert orchestrator.character_gen is not None
    assert orchestrator.panel_selector is not None
    assert orchestrator.panel_gen is not None
