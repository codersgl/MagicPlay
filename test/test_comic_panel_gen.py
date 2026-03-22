from pathlib import Path

import pytest

from magicplay.generators.comic_panel_gen import ComicPanelGenerator, PanelOutput


def test_comic_panel_generator_init():
    generator = ComicPanelGenerator(story_name="TestStory", episode_name="01")
    assert generator.story_name == "TestStory"
    assert generator.episode_name == "01"
    assert generator.style == "anime"


def test_comic_panel_generator_custom_style():
    generator = ComicPanelGenerator(
        story_name="TestStory", episode_name="01", style="comic"
    )
    assert generator.style == "comic"


def test_panel_output_structure():
    output = PanelOutput(
        panel_number=1,
        image_path=Path("/tmp/test_panel.png"),
        description="Test panel",
        dialogue="Hello!",
    )
    assert output.panel_number == 1
    assert output.description == "Test panel"
    assert output.dialogue == "Hello!"
    assert output.success is True
    assert output.error is None


def test_panel_output_failure():
    output = PanelOutput(
        panel_number=1,
        image_path=Path("/tmp/test_panel.png"),
        description="Test panel",
        dialogue="Hello!",
        success=False,
        error="API error",
    )
    assert output.success is False
    assert output.error == "API error"


def test_parse_resolution():
    """Test resolution string parsing."""
    result = ComicPanelGenerator._parse_resolution("1024*1024")
    assert result == (1024, 1024)

    result = ComicPanelGenerator._parse_resolution("1920*1080")
    assert result == (1920, 1080)

    # Test fallback for invalid input
    result = ComicPanelGenerator._parse_resolution("invalid")
    assert result == (1024, 1024)
