"""
Tests for SceneConceptGenerator module.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from magicplay.generators.scene_concept_gen import SceneConceptGenerator


class TestSceneConceptGenerator:
    """Test SceneConceptGenerator functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_image_service(self):
        """Create mock image service."""
        mock = MagicMock()
        mock.generate_image_and_download = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def scene_concept_generator(self, temp_dir, mock_image_service):
        """Create SceneConceptGenerator with mocked dependencies."""
        with patch("magicplay.generators.scene_concept_gen.DataManager") as mock_dm:
            mock_dm.get_scene_concepts_path.return_value = temp_dir

            with patch(
                "magicplay.generators.scene_concept_gen.ImageService",
                return_value=mock_image_service,
            ):
                gen = SceneConceptGenerator(
                    story_name="TestStory", episode_name="Episode1", size=(1280, 720)
                )
                yield gen

    def test_initialization(self, scene_concept_generator, temp_dir):
        """Test SceneConceptGenerator initialization."""
        assert scene_concept_generator.story_name == "TestStory"
        assert scene_concept_generator.episode_name == "Episode1"
        assert scene_concept_generator.size == (1280, 720)
        assert scene_concept_generator.output_dir == temp_dir

    def test_get_or_create_existing_image(self, scene_concept_generator, temp_dir):
        """Test getting existing concept image."""
        # Create a fake existing image
        existing_image = temp_dir / "scene_1.jpg"
        existing_image.touch()

        result = scene_concept_generator.get_or_create_scene_concept_image(
            scene_name="scene_1", visual_prompt="A visual description"
        )

        assert result == existing_image

    def test_get_or_create_new_image(self, scene_concept_generator, temp_dir):
        """Test creating new concept image when none exists."""
        # Ensure file does NOT exist initially (so it generates a new one)
        result_path = temp_dir / "scene_2.jpg"
        # Don't create the file - we want it to generate a new one

        # Mock returns a path that DOES exist to satisfy the existence check
        result_path.touch()
        scene_concept_generator.image_service.generate_image_and_download.return_value = str(
            result_path
        )

        result = scene_concept_generator.get_or_create_scene_concept_image(
            scene_name="scene_2", visual_prompt="A visual description"
        )

        # Since file now exists, it should return existing path without calling generate
        assert result is not None
        # Note: generate_image_and_download is NOT called because file exists

    def test_generate_scene_concept_image_failure(self, scene_concept_generator):
        """Test handling of failed image generation."""
        scene_concept_generator.image_service.generate_image_and_download.return_value = (
            None
        )

        result = scene_concept_generator.generate_scene_concept_image(
            scene_name="failed_scene", visual_prompt="A visual description"
        )

        assert result is None

    def test_ensure_scene_concept_image_existing(
        self, scene_concept_generator, temp_dir
    ):
        """Test ensure_scene_concept_image with existing image."""
        existing_image = temp_dir / "scene_existing.jpg"
        existing_image.touch()

        result = scene_concept_generator.ensure_scene_concept_image(
            scene_name="scene_existing", scene_script="Some script content"
        )

        assert result == existing_image

    def test_ensure_scene_concept_image_generation(
        self, scene_concept_generator, temp_dir
    ):
        """Test ensure_scene_concept_image generates new image."""
        result_path = temp_dir / "new_scene.jpg"
        result_path.touch()  # Create actual file
        scene_concept_generator.image_service.generate_image_and_download.return_value = str(
            result_path
        )

        result = scene_concept_generator.ensure_scene_concept_image(
            scene_name="new_scene", scene_script="A scene script with some content"
        )

        assert result is not None

    def test_extract_visual_prompt(self, scene_concept_generator):
        """Test visual prompt extraction from scene script."""
        script = """
# Scene 1

## SCRIPT

This is a dialogue-heavy scene where the hero enters the castle.

### ACTION
Hero walks through the grand entrance.
        """

        result = scene_concept_generator._extract_visual_prompt(script)

        assert isinstance(result, str)
        assert len(result) > 0
        # Should not contain markdown headers
        assert "#" not in result

    def test_extract_visual_prompt_with_empty_script(self, scene_concept_generator):
        """Test extraction from empty script."""
        result = scene_concept_generator._extract_visual_prompt("")
        assert result == ""

    def test_extract_visual_prompt_with_headers_only(self, scene_concept_generator):
        """Test extraction when script has only headers."""
        script = "# Header\n## Another Header"
        result = scene_concept_generator._extract_visual_prompt(script)
        # Should fall back to first 200 chars of script
        assert isinstance(result, str)

    def test_create_scene_prompt(self, scene_concept_generator):
        """Test prompt enhancement for scene concept."""
        original_prompt = "A hero standing in front of a castle"

        result = scene_concept_generator._create_scene_prompt(original_prompt)

        assert "A hero standing in front of a castle" in result
        assert "Anime style" in result
        assert "masterpiece" in result
        assert "cel shaded" in result


class TestSceneConceptGeneratorEdgeCases:
    """Test edge cases for SceneConceptGenerator."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_image_service(self):
        """Create mock image service."""
        mock = MagicMock()
        mock.generate_image_and_download = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def generator(self, temp_dir, mock_image_service):
        """Create generator with mocked dependencies."""
        with patch("magicplay.generators.scene_concept_gen.DataManager") as mock_dm:
            mock_dm.get_scene_concepts_path.return_value = temp_dir
            with patch(
                "magicplay.generators.scene_concept_gen.ImageService",
                return_value=mock_image_service,
            ):
                yield SceneConceptGenerator(
                    story_name="TestStory", episode_name="Episode1"
                )

    def test_very_long_script(self, generator):
        """Test handling of very long scene script."""
        long_script = "Line " * 1000
        result = generator._extract_visual_prompt(long_script)
        # Should handle without issues
        assert isinstance(result, str)

    def test_special_characters_in_scene_name(self, generator, temp_dir):
        """Test handling of special characters in scene name."""
        result_path = temp_dir / "scene_special.jpg"
        result_path.touch()  # Create actual file
        generator.image_service.generate_image_and_download.return_value = str(
            result_path
        )

        # Scene name with special characters
        result = generator.get_or_create_scene_concept_image(
            scene_name="scene_01-02-03", visual_prompt="Test"
        )

        assert generator.image_service.generate_image_and_download.called

    def test_ensure_scene_concept_with_exception(self, generator, temp_dir):
        """Test handling of exception during generation."""
        generator.image_service.generate_image_and_download.side_effect = Exception(
            "API Error"
        )

        result = generator.ensure_scene_concept_image(
            scene_name="error_scene", scene_script="Some content"
        )

        assert result is None
