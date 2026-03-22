"""
Tests for ScriptGenerator module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from magicplay.config import Settings
from magicplay.generators.script_gen import ScriptGenerator
from test.mocks import MockLLMService


class TestScriptGenerator:
    """Test ScriptGenerator functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return Settings(
            deepseek_api_key="test-key",
            dashscope_api_key="test-key",
            project_root=Path(tempfile.mkdtemp()),
        )

    @pytest.fixture
    def mock_llm(self, mock_settings):
        """Create mock LLM service."""
        llm = MockLLMService(mock_settings)
        llm.set_mock_response("Generated script content")
        return llm

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def script_generator(self, mock_settings, mock_llm, temp_output_dir):
        """Create ScriptGenerator instance with mocked dependencies."""
        gen = ScriptGenerator(
            config=mock_settings,
            llm_service=mock_llm,
            output_dir=temp_output_dir,
            min_scene_length=100,
            max_scene_length=5000,
            genre="Xuanhuan",
            reference_story="Test Reference Story",
        )
        return gen

    def test_initialization(self, script_generator, mock_settings, temp_output_dir):
        """Test ScriptGenerator initialization."""
        assert script_generator.name == "script_generator"
        assert script_generator.config == mock_settings
        assert script_generator.output_dir == temp_output_dir
        assert script_generator.min_scene_length == 100
        assert script_generator.max_scene_length == 5000
        assert script_generator.genre == "Xuanhuan"
        assert script_generator.reference_story == "Test Reference Story"

    def test_initialization_with_defaults(self, mock_settings, mock_llm):
        """Test initialization with default values."""
        gen = ScriptGenerator(config=mock_settings, llm_service=mock_llm)
        assert gen.min_scene_length == 600  # default (optimised for 5-10s video)
        assert gen.max_scene_length == 2000  # default (optimised for 5-10s video)
        assert gen.genre == ""
        assert gen.reference_story == ""

    def test_load_prompt_templates(self, script_generator):
        """Test prompt templates are loaded."""
        # Should have loaded fallback templates since actual files may not exist
        assert hasattr(script_generator, "story_prompt_template")
        assert hasattr(script_generator, "episode_prompt_template")
        assert hasattr(script_generator, "scene_prompt_template")
        assert isinstance(script_generator.story_prompt_template, str)
        assert isinstance(script_generator.episode_prompt_template, str)
        assert isinstance(script_generator.scene_prompt_template, str)

    def test_generate_story_outline(self, script_generator, mock_llm):
        """Test story outline generation."""
        result = script_generator.generate_story_outline("A hero's journey")
        assert result == "Generated script content"
        assert mock_llm.call_count >= 1
        # Check that the idea was included in the prompt
        last_call = mock_llm.last_prompts[-1]
        assert "A hero's journey" in last_call["user"]

    def test_generate_story_outline_with_genre(self, script_generator, mock_llm):
        """Test story outline generation with genre."""
        script_generator.genre = "Xuanhuan"
        result = script_generator.generate_story_outline("Cultivation story")
        assert result == "Generated script content"
        last_call = mock_llm.last_prompts[-1]
        assert "Xuanhuan" in last_call["user"]

    def test_generate_episode_outline(self, script_generator, mock_llm):
        """Test episode outline generation."""
        story_context = "Hero discovered powers"
        episode_idea = "First battle"
        result = script_generator.generate_episode_outline(story_context, episode_idea)
        assert result == "Generated script content"
        last_call = mock_llm.last_prompts[-1]
        assert "Hero discovered powers" in last_call["user"]
        assert "First battle" in last_call["user"]

    def test_generate_scene_script(self, script_generator, mock_llm, temp_output_dir):
        """Test scene script generation."""
        result = script_generator.generate_scene_script(
            scene_name="scene_1",
            story_context="Hero's backstory",
            episode_context="First episode",
            memory="Previous scene ended with cliffhanger",
            scene_prompt="Battle scene with intense action",
            character_profiles={"Hero": "Hero [Visual Tags: black hair, blue eyes]"},
        )
        assert isinstance(result, Path)
        assert result.name == "scene_1.md"
        assert result.parent == temp_output_dir
        assert result.exists()

        content = result.read_text()
        assert "Generated script content" in content

    def test_generate_scene_script_with_character_profiles(
        self, script_generator, mock_llm, temp_output_dir
    ):
        """Test scene script generation includes character profiles."""
        character_profiles = {
            "Zhang Wei": "Zhang Wei [Visual Tags: black hair, scar on cheek]",
            "Mei Ling": "Mei Ling [Visual Tags: long black hair, elegant]",
        }
        result = script_generator.generate_scene_script(
            scene_name="scene_with_chars", character_profiles=character_profiles
        )
        assert result.exists()

    def test_generate_scene_script_creates_directory(
        self, script_generator, mock_llm, temp_output_dir
    ):
        """Test that scene script creates nested directories."""
        nested_scene = "episode1/scene1"
        result = script_generator.generate_scene_script(
            scene_name=nested_scene,
        )
        assert result.exists()
        assert "episode1" in str(result)

    def test_generate_visual_prompt(self, script_generator, mock_llm, temp_output_dir):
        """Test visual prompt generation from script."""
        # Create a mock script file
        script_file = temp_output_dir / "test_script.md"
        script_file.write_text("Mock script content for testing", encoding="utf-8")

        result = script_generator.generate_visual_prompt(
            script_path=script_file,
            character_profiles={"Hero": "Hero [Visual Tags: black hair]"},
            visual_style="Cinematic dark fantasy",
        )
        assert result == "Generated script content"
        assert mock_llm.call_count >= 1

    def test_generate_visual_prompt_file_not_found(self, script_generator):
        """Test visual prompt generation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            script_generator.generate_visual_prompt(
                script_path="/nonexistent/path/script.md"
            )

    def test_generate_with_empty_result_raises_error(
        self, script_generator, mock_llm, temp_output_dir
    ):
        """Test that empty LLM result raises RuntimeError."""
        mock_llm.set_mock_response("")  # Empty response

        with pytest.raises(RuntimeError) as exc_info:
            script_generator.generate_scene_script(scene_name="empty_test")
        assert "Failed to generate" in str(exc_info.value)


class TestScriptGeneratorContext:
    """Test ScriptGenerator with GenerationContext."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return Settings(
            deepseek_api_key="test-key",
            dashscope_api_key="test-key",
            project_root=Path(tempfile.mkdtemp()),
        )

    @pytest.fixture
    def mock_llm(self, mock_settings):
        """Create mock LLM service."""
        llm = MockLLMService(mock_settings)
        llm.set_mock_response("Generated script content")
        return llm

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def script_generator(self, mock_settings, mock_llm, temp_output_dir):
        """Create ScriptGenerator instance."""
        return ScriptGenerator(
            config=mock_settings,
            llm_service=mock_llm,
            output_dir=temp_output_dir,
        )

    def test_generate_with_context(self, script_generator, mock_llm):
        """Test generate method with GenerationContext."""
        from magicplay.generators.base import GenerationContext

        context = GenerationContext(
            story_name="TestStory",
            episode_name="Episode1",
            scene_name="context_scene",
            story_context="A fantasy world",
            episode_context="Episode 1",
            memory="Previous events",
            scene_prompt="An epic battle",
        )

        result = script_generator.generate(context)
        assert result.success
        assert result.data is not None
        assert mock_llm.call_count >= 1

    def test_generate_with_empty_scene_name_uses_default(
        self, script_generator, mock_llm, temp_output_dir
    ):
        """Test that empty scene_name uses default 'scene_1'."""
        from magicplay.generators.base import GenerationContext

        context = GenerationContext(
            story_name="TestStory",
            episode_name="Episode1",
            scene_name="",  # Empty
            story_context="Context",
        )

        result = script_generator.generate(context)
        assert result.success
        # Check that file was created with default name
        scene_file = temp_output_dir / "scene_1.md"
        assert scene_file.exists()
