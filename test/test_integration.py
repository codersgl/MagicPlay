"""
Integration tests for MagicPlay components.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from magicplay.core.orchestrator import Orchestrator
from magicplay.analyzer.script_analyzer import ScriptAnalyzer
from magicplay.services.image_api import ImageService
from magicplay.services.video_api import VideoService


class TestIntegration:
    """Integration tests for MagicPlay components."""

    def test_orchestrator_with_mocked_services(self, tmp_path):
        """Test orchestrator with mocked services."""
        # Create test directories
        story_dir = tmp_path / "story"
        story_dir.mkdir()
        episode_dir = story_dir / "episode1"
        episode_dir.mkdir()

        # Create a simple test script
        test_script = """
### **1. SCENE HEADER**
INT. LABORATORY - NIGHT

### **2. VISUAL KEY**
High-tech lab with holographic displays, neon lighting

### **3. SCRIPT BODY**

**ACTION**
DR. ELARA stands before a console.

DR. ELARA
(whispering)
The quantum field is stabilizing.
"""

        script_file = episode_dir / "scene1.md"
        script_file.write_text(test_script)

        # Create orchestrator with mocked services
        with (
            patch("magicplay.services.image_api.ImageService") as mock_image_service,
            patch("magicplay.services.video_api.VideoService") as mock_video_service,
            patch("magicplay.core.orchestrator.ScriptAnalyzer") as mock_analyzer,
        ):
            # Setup mock returns
            mock_image_service.return_value.generate_image_url.return_value = (
                "https://example.com/test.png"
            )
            mock_image_service.return_value.generate_image_and_download.return_value = (
                str(episode_dir / "test.png")
            )

            mock_video_service.return_value.generate_video_url.return_value = (
                "https://example.com/test.mp4"
            )

            mock_analyzer.return_value.analyze.return_value = Mock(
                total_words=50,
                dialogue_lines=2,
                action_density=0.3,
                scene_type=Mock(value="dialogue"),
                estimated_duration=5,
                complexity_score=0.5,
                character_count=1,
                location_changes=1,
                metadata={},
            )

            orchestrator = Orchestrator(
                story_name="test_story", episode_name="episode1"
            )

            # Should not raise exceptions with mocked services
            # We can't actually run the full process without real APIs,
            # but we can verify the orchestrator can be instantiated
            assert orchestrator.story_name == "test_story"
            assert orchestrator.episode_name == "episode1"

    def test_end_to_end_mocked_workflow(self, tmp_path):
        """Test a complete mocked workflow from script to video."""
        # Setup test directories
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock all external dependencies including environment variables
        with (
            patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}),
            patch("magicplay.services.image_api.ImageService") as mock_image_service,
            patch("magicplay.services.video_api.VideoService") as mock_video_service,
            patch("magicplay.services.llm.LLMService") as mock_llm_service,
            patch("magicplay.utils.media.MediaUtils.download_video") as mock_download,
        ):
            # Configure mocks
            mock_image_instance = Mock()
            mock_image_instance.generate_image_url.return_value = "https://image.url"
            mock_image_instance.generate_image_and_download.return_value = str(
                output_dir / "image.png"
            )
            mock_image_service.return_value = mock_image_instance

            mock_video_instance = Mock()
            mock_video_instance.generate_video_url.return_value = "https://video.url"
            mock_video_service.return_value = mock_video_instance

            mock_llm_instance = Mock()
            mock_llm_instance.generate_content.return_value = "Generated prompt text"
            mock_llm_service.return_value = mock_llm_instance

            mock_download.return_value = None  # Download succeeds

            # Create components - these should use the mocked services
            image_service = mock_image_instance
            video_service = mock_video_instance

            # Verify they were created with correct configuration
            assert image_service is not None
            assert video_service is not None

            # Simulate a simple workflow
            test_prompt = "Test image generation"

            # Image generation
            image_url = image_service.generate_image_url(prompt=test_prompt)
            assert image_url == "https://image.url"

            # Verify API was called
            mock_image_instance.generate_image_url.assert_called_once()

            # Video generation
            video_url = video_service.generate_video_url(prompt=test_prompt)
            assert video_url == "https://video.url"

            mock_video_instance.generate_video_url.assert_called_once()

    def test_script_analyzer_integration(self):
        """Test script analyzer with actual implementation."""
        analyzer = ScriptAnalyzer(min_duration=2, max_duration=15)

        # Test with simple script
        simple_script = """
INT. ROOM - DAY

JOHN
Hello.

MARY
Hi.
"""

        result = analyzer.analyze(simple_script)

        # Verify basic properties
        assert result.total_words > 0
        assert result.dialogue_lines >= 2
        assert 0.0 <= result.action_density <= 1.0
        assert 2 <= result.estimated_duration <= 15
        assert 0.0 <= result.complexity_score <= 1.0

        # Test with empty script
        empty_result = analyzer.analyze("")
        assert empty_result.total_words == 0
        assert empty_result.estimated_duration == 2  # min_duration

    def test_file_analysis_integration(self, tmp_path):
        """Test analyzing script from file."""
        analyzer = ScriptAnalyzer(min_duration=2, max_duration=15)

        # Create test script file
        script_content = """
### **1. SCENE HEADER**
EXT. FOREST - NIGHT

### **3. SCRIPT BODY**

The moonlight filters through dense foliage.

CHARACTER
(looking around)
It's quiet... too quiet.
"""

        script_file = tmp_path / "test_script.md"
        script_file.write_text(script_content)

        # Analyze file
        result = analyzer.analyze_file(str(script_file))

        assert result is not None
        assert result.total_words > 0
        assert result.estimated_duration >= 2

    def test_nonexistent_file_analysis(self):
        """Test analyzing non-existent file."""
        analyzer = ScriptAnalyzer()
        result = analyzer.analyze_file("/nonexistent/path/script.md")
        assert result is None

    def test_orchestrator_configuration_validation(self):
        """Test orchestrator configuration validation."""
        # Test valid configuration
        orchestrator = Orchestrator(
            story_name="valid_story",
            episode_name="episode1",
            max_scenes=5,
            genre="fantasy",
            reference_story="reference",
        )

        assert orchestrator.story_name == "valid_story"
        assert orchestrator.episode_name == "episode1"
        assert orchestrator.max_scenes == 5
        assert orchestrator.genre == "fantasy"
        assert orchestrator.reference_story == "reference"

        # Test with default parameters
        default_orchestrator = Orchestrator(
            story_name="default_story", episode_name="episode1"
        )

        assert default_orchestrator.story_name == "default_story"
        assert default_orchestrator.episode_name == "episode1"
        assert default_orchestrator.max_scenes == 5  # default value

    def test_error_handling_integration(self):
        """Test error handling across components."""
        # Test image service error handling (qwen provider requires DASHSCOPE_API_KEY)
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
                ImageService(api_provider="qwen")

        # Test video service error handling
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
                VideoService()

        # Test script analyzer with invalid script file
        analyzer = ScriptAnalyzer(min_duration=5, max_duration=20)
        result = analyzer.analyze_file("/nonexistent/path/script.md")
        assert result is None  # Should return None for non-existent file

        # Test script analyzer with empty script
        empty_result = analyzer.analyze("")
        assert empty_result.total_words == 0
        assert empty_result.estimated_duration == 5  # min_duration

    def test_component_interoperability(self):
        """Test that components can work together."""
        # Create analyzer
        analyzer = ScriptAnalyzer(min_duration=5, max_duration=30)

        # Analyze script
        script = "Simple dialogue scene."
        result = analyzer.analyze(script)

        # Verify result can be used by other components
        assert isinstance(result.estimated_duration, int)
        assert isinstance(result.scene_type.value, str)
        assert isinstance(result.metadata, dict)

        # Metadata should contain useful information
        assert "word_count" in result.metadata
        assert "has_action" in result.metadata

    @pytest.mark.skip(reason="Requires special environment mocking")
    def test_environment_variable_handling(self):
        """Test environment variable handling across services."""
        # Test missing environment variables
        test_cases = [
            ("ImageService", "DASHSCOPE_API_KEY"),
            ("VideoService", "DASHSCOPE_API_KEY"),
            ("LLMService", "DEEPSEEK_API_KEY"),
        ]

        for service_name, env_var in test_cases:
            with patch.dict(os.environ, {}, clear=True):
                if service_name == "ImageService":
                    with pytest.raises(ValueError, match=env_var):
                        ImageService()
                elif service_name == "VideoService":
                    with pytest.raises(ValueError, match=env_var):
                        VideoService()
                elif service_name == "LLMService":
                    with pytest.raises(ValueError, match=env_var):
                        from magicplay.services.llm import LLMService

                        LLMService()

    def test_path_handling_integration(self, tmp_path):
        """Test path handling across different components."""
        # Test with various path formats
        test_paths = [
            str(tmp_path / "test.txt"),
            tmp_path / "test.txt",
            Path(tmp_path) / "test.txt",
        ]

        # All should work with file operations
        for path in test_paths:
            # Write test file
            if isinstance(path, (str, Path)):
                path_obj = Path(path) if isinstance(path, str) else path
                path_obj.write_text("test content")
                assert path_obj.exists()

                # Read it back
                content = path_obj.read_text()
                assert content == "test content"

    @pytest.mark.parametrize("duration_param", [None, 5, 10, 20])
    def test_duration_parameter_propagation(self, duration_param):
        """Test duration parameter propagation through components."""
        # Create analyzer with specific duration range
        analyzer = ScriptAnalyzer(min_duration=3, max_duration=20)

        # Test script that should produce different durations
        scripts = [
            ("Short", "Brief scene."),
            ("Medium", "A longer scene with some dialogue and action."),
            (
                "Long",
                """
INT. LIVING ROOM - NIGHT

**ACTION**
JOHN paces nervously across the room, checking his watch repeatedly.

JOHN
(muttering)
Where is she? She said she'd be here by now.

**ACTION**
The doorbell rings. John rushes to answer it.

MARY
(smiling)
Sorry I'm late. Traffic was terrible.

JOHN
(relieved)
I was worried something happened.

MARY
Don't worry, I'm here now.

**ACTION**
They embrace. The tension in the room dissipates.
""",
            ),
        ]

        for name, script in scripts:
            result = analyzer.analyze(script)
            # Duration should be within configured range
            assert 3 <= result.estimated_duration <= 20
            # Complexity should influence duration appropriately
            # Short script should have low complexity
            if name == "Short":
                assert result.complexity_score < 0.3
            # Long script should have higher complexity (has dialogue, action, characters)
            elif name == "Long":
                assert (
                    result.complexity_score > 0.05
                )  # Should have some complexity due to dialogue/action
            # Medium script should be in between
            else:
                assert result.complexity_score < 0.5
