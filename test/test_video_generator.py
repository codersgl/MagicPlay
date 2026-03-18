"""
Pytest tests for VideoGenerator.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from magicplay.generators.video_gen import VideoGenerator


class TestVideoGenerator:
    """Test VideoGenerator functionality."""

    @pytest.fixture
    def video_generator(self):
        """Create a VideoGenerator instance for tests."""
        return VideoGenerator()

    def test_video_generator_initialization(self):
        """Test VideoGenerator initialization with default parameters."""
        generator = VideoGenerator()
        
        assert generator.size == (1280, 720)
        assert generator.duration == 15
        assert generator.service.api_provider == "qwen"

    def test_video_generator_initialization_custom_params(self):
        """Test VideoGenerator initialization with custom parameters."""
        generator = VideoGenerator(
            api_provider="test_provider",
            size=(1920, 1080),
            duration=10
        )
        
        assert generator.size == (1920, 1080)
        assert generator.duration == 10
        # Note: We can't easily check the service's api_provider without mocking

    def test_generate_video_without_reference(self, video_generator, tmp_path):
        """Test video generation without reference image."""
        visual_prompt = "A beautiful sunset over mountains"
        output_path = tmp_path / "test_video.mp4"
        
        # Mock the service and MediaUtils
        with patch.object(video_generator.service, 'generate_video_url') as mock_generate_url, \
             patch('magicplay.generators.video_gen.MediaUtils') as mock_media_utils:
            
            # Setup mocks
            mock_generate_url.return_value = "http://test.com/video.mp4"
            mock_media_utils.download_video.return_value = True
            
            # Call the method
            result_path = video_generator.generate_video(
                visual_prompt=visual_prompt,
                output_path=output_path
            )
            
            # Verify calls
            mock_generate_url.assert_called_once()
            call_args = mock_generate_url.call_args
            
            # Check the prompt was passed
            assert call_args.kwargs['prompt'] == visual_prompt
            assert call_args.kwargs['size'] == video_generator.size
            assert call_args.kwargs['duration'] == video_generator.duration
            assert call_args.kwargs['ref_img_path'] is None
            
            # Check MediaUtils.download_video was called
            mock_media_utils.download_video.assert_called_once_with(
                "http://test.com/video.mp4", output_path
            )
            
            assert result_path == output_path

    def test_generate_video_with_reference(self, video_generator, tmp_path):
        """Test video generation with reference image."""
        visual_prompt = "A continuation of previous scene"
        output_path = tmp_path / "test_video.mp4"
        ref_img_path = tmp_path / "reference.jpg"
        ref_img_path.write_text("dummy image content")  # Create dummy file
        
        with patch.object(video_generator.service, 'generate_video_url') as mock_generate_url, \
             patch('magicplay.generators.video_gen.MediaUtils') as mock_media_utils:
            
            mock_generate_url.return_value = "http://test.com/video2.mp4"
            mock_media_utils.download_video.return_value = True
            
            result_path = video_generator.generate_video(
                visual_prompt=visual_prompt,
                output_path=output_path,
                ref_img_path=ref_img_path
            )
            
            # Verify reference image path was passed
            mock_generate_url.assert_called_once()
            call_args = mock_generate_url.call_args
            assert call_args.kwargs['ref_img_path'] == str(ref_img_path)

    def test_generate_video_with_custom_duration(self, video_generator, tmp_path):
        """Test video generation with custom duration parameter."""
        visual_prompt = "Test prompt"
        output_path = tmp_path / "test_video.mp4"
        custom_duration = 8
        
        with patch.object(video_generator.service, 'generate_video_url') as mock_generate_url, \
             patch('magicplay.generators.video_gen.MediaUtils') as mock_media_utils:
            
            mock_generate_url.return_value = "http://test.com/video.mp4"
            mock_media_utils.download_video.return_value = True
            
            result_path = video_generator.generate_video(
                visual_prompt=visual_prompt,
                output_path=output_path,
                duration=custom_duration
            )
            
            # Verify custom duration was used
            mock_generate_url.assert_called_once()
            call_args = mock_generate_url.call_args
            assert call_args.kwargs['duration'] == custom_duration

    def test_generate_video_download_failure(self, video_generator, tmp_path):
        """Test video generation when download fails."""
        visual_prompt = "Test prompt"
        output_path = tmp_path / "test_video.mp4"
        
        with patch.object(video_generator.service, 'generate_video_url') as mock_generate_url, \
             patch('magicplay.generators.video_gen.MediaUtils') as mock_media_utils:
            
            mock_generate_url.return_value = "http://test.com/video.mp4"
            mock_media_utils.download_video.return_value = False
            
            # Should raise RuntimeError
            with pytest.raises(RuntimeError, match="Failed to download generated video"):
                video_generator.generate_video(
                    visual_prompt=visual_prompt,
                    output_path=output_path
                )

    def test_generate_video_service_exception(self, video_generator, tmp_path):
        """Test video generation when service raises exception."""
        visual_prompt = "Test prompt"
        output_path = tmp_path / "test_video.mp4"
        
        with patch.object(video_generator.service, 'generate_video_url') as mock_generate_url:
            
            mock_generate_url.side_effect = Exception("API error")
            
            # Should raise RuntimeError with original exception message
            with pytest.raises(RuntimeError, match="Video generation failed: API error"):
                video_generator.generate_video(
                    visual_prompt=visual_prompt,
                    output_path=output_path
                )

    def test_generate_video_creates_output_directory(self, video_generator, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        visual_prompt = "Test prompt"
        output_dir = tmp_path / "nested" / "deep" / "dir"
        output_path = output_dir / "test_video.mp4"
        
        # Verify directory doesn't exist yet
        assert not output_dir.exists()
        
        with patch.object(video_generator.service, 'generate_video_url') as mock_generate_url, \
             patch('magicplay.generators.video_gen.MediaUtils') as mock_media_utils:
            
            mock_generate_url.return_value = "http://test.com/video.mp4"
            mock_media_utils.download_video.return_value = True
            
            result_path = video_generator.generate_video(
                visual_prompt=visual_prompt,
                output_path=output_path
            )
            
            # Directory should have been created
            assert output_dir.exists()
            assert result_path == output_path

    def test_generate_video_handles_string_path(self, video_generator, tmp_path):
        """Test that generate_video accepts string paths."""
        visual_prompt = "Test prompt"
        output_path = tmp_path / "test_video.mp4"
        
        with patch.object(video_generator.service, 'generate_video_url') as mock_generate_url, \
             patch('magicplay.generators.video_gen.MediaUtils') as mock_media_utils:
            
            mock_generate_url.return_value = "http://test.com/video.mp4"
            mock_media_utils.download_video.return_value = True
            
            # Pass string path instead of Path object
            result_path = video_generator.generate_video(
                visual_prompt=visual_prompt,
                output_path=str(output_path)
            )
            
            assert isinstance(result_path, Path)
            assert result_path == output_path

    @pytest.mark.parametrize("duration_param", [None, 5, 12, 20])
    def test_duration_parameter_handling(self, duration_param, tmp_path):
        """Test various duration parameter scenarios."""
        generator = VideoGenerator(duration=15)  # Default duration 15
        
        visual_prompt = "Test prompt"
        output_path = tmp_path / "test_video.mp4"
        
        with patch.object(generator.service, 'generate_video_url') as mock_generate_url, \
             patch('magicplay.generators.video_gen.MediaUtils') as mock_media_utils:
            
            mock_generate_url.return_value = "http://test.com/video.mp4"
            mock_media_utils.download_video.return_value = True
            
            generator.generate_video(
                visual_prompt=visual_prompt,
                output_path=output_path,
                duration=duration_param
            )
            
            # Check which duration was used
            expected_duration = duration_param if duration_param is not None else generator.duration
            call_args = mock_generate_url.call_args
            assert call_args.kwargs['duration'] == expected_duration