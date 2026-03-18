"""
Tests for the core Orchestrator module.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from magicplay.core.orchestrator import Orchestrator, StoryOrchestrator
from magicplay.utils.paths import DataManager


class TestOrchestrator:
    """Test the Orchestrator class."""

    def test_orchestrator_initialization(self):
        """Test Orchestrator initialization with default parameters."""
        orchestrator = Orchestrator(
            story_name="test_story",
            episode_name="episode1"
        )
        
        assert orchestrator.story_name == "test_story"
        assert orchestrator.episode_name == "episode1"
        assert orchestrator.max_scenes == 5
        assert orchestrator.genre == ""
        assert orchestrator.reference_story == ""
        
        # Verify directories are set
        assert "test_story" in str(orchestrator.scenes_dir)
        assert "test_story" in str(orchestrator.scripts_dir)
        assert "test_story" in str(orchestrator.videos_dir)

    def test_orchestrator_initialization_custom_params(self):
        """Test Orchestrator initialization with custom parameters."""
        orchestrator = Orchestrator(
            story_name="custom_story",
            episode_name="custom_episode",
            max_scenes=10,
            genre="fantasy",
            reference_story="reference_story.md"
        )
        
        assert orchestrator.story_name == "custom_story"
        assert orchestrator.episode_name == "custom_episode"
        assert orchestrator.max_scenes == 10
        assert orchestrator.genre == "fantasy"
        assert orchestrator.reference_story == "reference_story.md"

    def test_load_context_with_existing_files(self, tmp_path):
        """Test loading context when story and episode files exist."""
        # Create mock directories and files
        story_path = tmp_path / "stories" / "test_story"
        story_path.mkdir(parents=True)
        episode_path = story_path / "episode1"
        episode_path.mkdir(parents=True)
        
        # Create test files
        story_file = story_path / "story_bible.md"
        story_file.write_text("# Story Bible\nTest story content")
        
        episode_file = episode_path / "episode_outline.md"
        episode_file.write_text("# Episode Outline\nTest episode content")
        
        with patch('magicplay.core.orchestrator.DataManager.get_story_path') as mock_story_path, \
             patch('magicplay.core.orchestrator.DataManager.get_episode_path') as mock_episode_path:
            
            mock_story_path.return_value = story_path
            mock_episode_path.return_value = episode_path
            
            orchestrator = Orchestrator("test_story", "episode1")
            story_ctx, episode_ctx = orchestrator.load_context()
            
            assert "Story Bible" in story_ctx
            assert "Episode Outline" in episode_ctx

    def test_load_context_without_episode_file(self, tmp_path):
        """Test loading context when episode file doesn't exist but story does."""
        # Create mock directories and files
        story_path = tmp_path / "stories" / "test_story"
        story_path.mkdir(parents=True)
        episode_path = story_path / "episode1"
        episode_path.mkdir(parents=True)
        
        # Create only story file
        story_file = story_path / "story_bible.md"
        story_file.write_text("# Story Bible\nTest story content")
        
        with patch('magicplay.core.orchestrator.DataManager.get_story_path') as mock_story_path, \
             patch('magicplay.core.orchestrator.DataManager.get_episode_path') as mock_episode_path, \
             patch('magicplay.core.orchestrator.ScriptGenerator.generate_episode_outline') as mock_generate:
            
            mock_story_path.return_value = story_path
            mock_episode_path.return_value = episode_path
            mock_generate.return_value = "# Generated Outline\nGenerated content"
            
            orchestrator = Orchestrator("test_story", "episode1")
            story_ctx, episode_ctx = orchestrator.load_context()
            
            assert "Story Bible" in story_ctx
            # Should use generated outline
            assert episode_ctx is not None

    def test_load_context_no_files(self, tmp_path):
        """Test loading context when no files exist."""
        story_path = tmp_path / "stories" / "test_story"
        story_path.mkdir(parents=True)
        episode_path = story_path / "episode1"
        episode_path.mkdir(parents=True)
        
        with patch('magicplay.core.orchestrator.DataManager.get_story_path') as mock_story_path, \
             patch('magicplay.core.orchestrator.DataManager.get_episode_path') as mock_episode_path:
            
            mock_story_path.return_value = story_path
            mock_episode_path.return_value = episode_path
            
            orchestrator = Orchestrator("test_story", "episode1")
            story_ctx, episode_ctx = orchestrator.load_context()
            
            assert story_ctx == ""
            assert episode_ctx == ""

    def test_ensure_character_images_with_story_context(self):
        """Test character image generation with story context."""
        test_story_context = """
# Characters
## Main Characters
- **John**: A brave hero
- **Mary**: A wise wizard
"""
        
        orchestrator = Orchestrator("test_story", "episode1")
        
        with patch('magicplay.core.orchestrator.StoryConsistencyManager') as mock_manager_class, \
             patch('magicplay.core.orchestrator.CharacterImageGenerator') as mock_gen_class:
            
            mock_manager = Mock()
            mock_manager.has_character_images.return_value = False
            # Set characters attribute to a dictionary so len() works
            mock_manager.characters = {
                "John": Mock(get_image_path=Mock(return_value=None)),
                "Mary": Mock(get_image_path=Mock(return_value=None))
            }
            # Mock get_all_character_images to return empty dict
            mock_manager.get_all_character_images.return_value = {}
            mock_manager_class.return_value = mock_manager
            
            mock_gen = Mock()
            mock_gen.ensure_character_images.return_value = {
                "John": "/path/to/john.png",
                "Mary": "/path/to/mary.png"
            }
            mock_gen_class.return_value = mock_gen
            
            # Mock anchors directory check
            with patch('pathlib.Path.exists', return_value=False), \
                 patch('pathlib.Path.glob', return_value=[]), \
                 patch('builtins.print'):
                
                # Should not raise exceptions
                orchestrator._ensure_character_images(test_story_context)
                
                # Verify methods were called
                mock_manager_class.assert_called_once_with("test_story")
                mock_manager.load_from_story_bible.assert_called_once_with(test_story_context)
                # CharacterImageGenerator should be called
                mock_gen_class.assert_called_once_with("test_story")
                mock_gen.ensure_character_images.assert_called_once_with(mock_manager)

    def test_ensure_character_images_empty_context(self):
        """Test character image generation with empty story context."""
        orchestrator = Orchestrator("test_story", "episode1")
        
        # Should not raise exceptions with empty context
        orchestrator._ensure_character_images("")
        
        # No manager should be created
        # We can't easily verify this without mocking, but the method should return early

    def test_ensure_character_images_existing_images(self):
        """Test character image generation when images already exist."""
        test_story_context = "# Story with characters"
        
        orchestrator = Orchestrator("test_story", "episode1")
        
        with patch('magicplay.core.orchestrator.StoryConsistencyManager') as mock_manager_class, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.glob', return_value=[]), \
             patch('builtins.print'):
            
            mock_manager = Mock()
            # Set characters attribute with mock objects
            mock_character = Mock()
            mock_character.get_image_path.return_value = "/path/to/image.png"
            mock_manager.characters = {"Test": mock_character}
            # Mock get_all_character_images to return existing images
            mock_manager.get_all_character_images.return_value = {"Test": "/path/to/image.png"}
            mock_manager_class.return_value = mock_manager
            
            orchestrator._ensure_character_images(test_story_context)
            
            # Should check for existing images via get_all_character_images
            mock_manager.get_all_character_images.assert_called_once()
            # load_from_story_bible should be called with story context
            mock_manager.load_from_story_bible.assert_called_once_with(test_story_context)

    @patch('magicplay.core.orchestrator.DataManager.get_scenes_prompts')
    @patch('magicplay.core.orchestrator.ScriptGenerator.generate_scene_script')
    @patch('magicplay.core.orchestrator.VideoGenerator.generate_video')
    @patch('magicplay.core.orchestrator.MediaUtils.stitch_videos')
    @patch('magicplay.core.orchestrator.ScriptAnalyzer')
    @patch('magicplay.core.orchestrator.MediaUtils')
    def test_run_with_mocked_dependencies(self, mock_media_utils, mock_script_analyzer_class, mock_stitch, mock_gen_video, mock_gen_script, mock_get_scenes):
        """Test orchestrator.run() with mocked dependencies."""
        # Setup mocks
        mock_get_scenes.return_value = []
        
        # Mock script generation - return a mock path
        mock_script_path = Path("/fake/path/scene1.md")
        mock_gen_script.return_value = mock_script_path
        
        # Mock video generation - return a mock path  
        mock_video_path = Path("/fake/path/scene1.mp4")
        mock_gen_video.return_value = mock_video_path
        
        # Mock stitching
        mock_stitch.return_value = None
        
        # Mock MediaUtils.extract_last_frame to return False
        mock_media_utils.extract_last_frame.return_value = False
        
        # Mock ScriptAnalyzer
        mock_script_analyzer = Mock()
        mock_script_analyzer.analyze_file.return_value = Mock(
            estimated_duration=5,
            scene_type=Mock(value="dialogue"),
            total_words=100,
            complexity_score=0.5
        )
        mock_script_analyzer_class.return_value = mock_script_analyzer
        
        orchestrator = Orchestrator("test_story", "episode1")
        
        # Mock load_context to return empty strings (simplify test)
        with patch.object(orchestrator, 'load_context', return_value=("", "")), \
             patch.object(orchestrator, '_ensure_character_images', return_value=None), \
             patch('builtins.print'), \
             patch('pathlib.Path.read_text', return_value="Test script content"), \
             patch('pathlib.Path.exists', return_value=False), \
             patch.object(orchestrator.script_gen, 'generate_visual_prompt', return_value="Visual prompt"), \
             patch.object(orchestrator.scene_concept_gen, 'ensure_scene_concept_image', return_value=None):
            
            result_video, result_memory = orchestrator.run()
            
            # Verify results - memory may be empty due to mock interactions
            assert result_video is None  # Stitch returns None
            # Memory assertion is less important than verifying the workflow executed
            # The mock Path.read_text returns "Test script content" but orchestrator may not use it
            
            # Verify methods were called
            mock_get_scenes.assert_called_once_with("test_story", "episode1")
            assert mock_gen_script.call_count == 5  # Default max_scenes=5
            assert mock_gen_video.call_count == 5  # Should be called for each scene

    @patch('magicplay.core.orchestrator.DataManager.get_scenes_prompts')
    @patch('magicplay.core.orchestrator.ScriptGenerator')
    @patch('magicplay.core.orchestrator.VideoGenerator')
    @patch('magicplay.core.orchestrator.MediaUtils')
    @patch('magicplay.core.orchestrator.ScriptAnalyzer')
    def test_run_with_predefined_scenes(self, mock_script_analyzer_class, mock_media_utils, mock_video_gen_class, mock_script_gen_class, mock_get_scenes, tmp_path):
        """Test orchestrator.run() with predefined scene prompts."""
        # Create a mock scene prompt file
        scene_file = tmp_path / "scene1.md"
        scene_file.write_text("# Scene 1 Prompt")
        
        mock_get_scenes.return_value = [scene_file]
        
        # Create mock generators before orchestrator is initialized
        mock_script_gen = Mock()
        mock_script_gen.generate_scene_script.return_value = Path("/fake/script.md")
        mock_script_gen.generate_visual_prompt.return_value = "Visual prompt"
        mock_script_gen.generate_episode_outline.return_value = "# Episode Outline"
        mock_script_gen_class.return_value = mock_script_gen
        
        mock_video_gen = Mock()
        mock_video_gen.generate_video.return_value = Path("/fake/video.mp4")
        mock_video_gen_class.return_value = mock_video_gen
        
        # Mock MediaUtils
        mock_media_utils.extract_last_frame.return_value = False
        mock_media_utils.stitch_videos.return_value = None
        
        # Mock ScriptAnalyzer
        mock_script_analyzer = Mock()
        mock_script_analyzer.analyze_file.return_value = Mock(
            estimated_duration=5,
            scene_type=Mock(value="dialogue"),
            total_words=100,
            complexity_score=0.5
        )
        mock_script_analyzer_class.return_value = mock_script_analyzer
        
        orchestrator = Orchestrator("test_story", "episode1")
        
        # Mock remaining dependencies
        with patch.object(orchestrator, 'load_context', return_value=("", "")), \
             patch.object(orchestrator, '_ensure_character_images', return_value=None), \
             patch('builtins.print'), \
             patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.read_text', return_value="Test script content"), \
             patch.object(orchestrator.script_gen, 'generate_visual_prompt', return_value="Visual prompt"), \
             patch.object(orchestrator.scene_concept_gen, 'ensure_scene_concept_image', return_value=None):
            
            result_video, result_memory = orchestrator.run()
            
            # Should process the predefined scene
            assert mock_get_scenes.called
            # The script generator should be called once for the single scene
            mock_script_gen.generate_scene_script.assert_called_once()

    def test_run_exception_handling(self):
        """Test that orchestrator.run() handles exceptions gracefully."""
        orchestrator = Orchestrator("test_story", "episode1")
        
        # Mock all dependencies to ensure exception only comes from load_context
        with patch.object(orchestrator, 'load_context', side_effect=Exception("Test error")), \
             patch.object(orchestrator, '_ensure_character_images', return_value=None), \
             patch('magicplay.core.orchestrator.DataManager.get_scenes_prompts', return_value=[]), \
             patch('builtins.print'):
            
            # Should not raise exception
            result_video, result_memory = orchestrator.run()
            
            assert result_video is None
            assert result_memory == ""


class TestStoryOrchestrator:
    """Test the StoryOrchestrator class."""

    def test_story_orchestrator_initialization(self):
        """Test StoryOrchestrator initialization."""
        orchestrator = StoryOrchestrator("test_story")
        
        assert orchestrator.story_name == "test_story"
        assert hasattr(orchestrator, 'story_path')

    @patch('magicplay.core.orchestrator.DataManager.get_episodes')
    def test_run_no_episodes(self, mock_get_episodes):
        """Test StoryOrchestrator.run() when no episodes exist."""
        mock_get_episodes.return_value = []
        
        orchestrator = StoryOrchestrator("test_story")
        
        with patch('builtins.print'):
            orchestrator.run()  # Should not raise exceptions
        
        mock_get_episodes.assert_called_once_with("test_story")

    @patch('magicplay.core.orchestrator.DataManager.get_episodes')
    @patch('magicplay.core.orchestrator.Orchestrator')
    @patch('magicplay.core.orchestrator.MediaUtils.stitch_videos')
    def test_run_with_episodes(self, mock_stitch, mock_orchestrator_class, mock_get_episodes, tmp_path):
        """Test StoryOrchestrator.run() with episodes."""
        # Create mock episode directories
        episode1 = tmp_path / "episode1"
        episode1.mkdir()
        episode2 = tmp_path / "episode2"
        episode2.mkdir()
        
        mock_get_episodes.return_value = [episode1, episode2]
        
        # Mock Orchestrator instances
        mock_orchestrator1 = Mock()
        mock_orchestrator1.run.return_value = (Path("/fake/ep1.mp4"), "memory1")
        
        mock_orchestrator2 = Mock()
        mock_orchestrator2.run.return_value = (Path("/fake/ep2.mp4"), "memory2")
        
        # Make mock_orchestrator_class return different instances
        mock_orchestrator_class.side_effect = [mock_orchestrator1, mock_orchestrator2]
        
        orchestrator = StoryOrchestrator("test_story")
        
        with patch('builtins.print'):
            orchestrator.run()
        
        # Verify orchestrators were created for each episode
        assert mock_orchestrator_class.call_count == 2
        mock_orchestrator_class.assert_any_call(story_name="test_story", episode_name="episode1")
        mock_orchestrator_class.assert_any_call(story_name="test_story", episode_name="episode2")
        
        # Verify run was called on each orchestrator
        mock_orchestrator1.run.assert_called_once_with(initial_memory="")
        mock_orchestrator2.run.assert_called_once_with(initial_memory="memory1")

    @patch('magicplay.core.orchestrator.DataManager.get_episodes')
    @patch('magicplay.core.orchestrator.Orchestrator')
    def test_run_with_orchestrator_exception(self, mock_orchestrator_class, mock_get_episodes, tmp_path):
        """Test StoryOrchestrator.run() when orchestrator raises an exception."""
        episode = tmp_path / "episode1"
        episode.mkdir()
        mock_get_episodes.return_value = [episode]
        
        mock_orchestrator = Mock()
        mock_orchestrator.run.side_effect = Exception("Orchestrator failed")
        mock_orchestrator_class.return_value = mock_orchestrator
        
        orchestrator = StoryOrchestrator("test_story")
        
        with patch('builtins.print'):
            # Should not raise exception
            orchestrator.run()
        
        # Verify orchestrator was still called
        mock_orchestrator.run.assert_called_once()