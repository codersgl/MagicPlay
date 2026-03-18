"""
Pytest tests for VideoService.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from http import HTTPStatus
import dashscope

from magicplay.services.video_api import VideoService


class TestVideoService:
    """Test VideoService functionality."""

    def test_video_service_initialization_missing_api_key(self):
        """Test VideoService initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DASHSCOPE_API_KEY environment variable is not set"):
                VideoService()

    def test_video_service_initialization_with_api_key(self):
        """Test VideoService initialization with API key."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            service = VideoService()
            assert service.api_provider == "qwen"
            assert service.api_key == "test_key"

    def test_video_service_initialization_custom_provider(self):
        """Test VideoService initialization with custom provider."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Currently only "qwen" provider is supported
            service = VideoService(api_provider="qwen")
            assert service.api_provider == "qwen"

    @pytest.fixture
    def video_service(self):
        """Create a VideoService instance for tests."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_api_key"}):
            return VideoService()

    @pytest.fixture
    def mock_video_response(self):
        """Create a mock video response for successful video generation."""
        response = Mock()
        response.status_code = HTTPStatus.OK
        response.output.video_url = "https://dashscope-result-sh.oss-cn-shanghai.aliyuncs.com/test_video.mp4"
        return response

    def test_generate_video_url_text_to_video_success(self, video_service, mock_video_response):
        """Test successful text-to-video URL generation."""
        test_prompt = "A beautiful sunset over mountains"
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            video_url = video_service.generate_video_url(
                prompt=test_prompt,
                size=(1280, 720),
                duration=5
            )
            
            # Verify API was called with correct parameters
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs
            
            assert call_kwargs['api_key'] == "test_api_key"
            assert call_kwargs['model'] == "wan2.6-t2v"
            assert call_kwargs['prompt'] == test_prompt
            assert call_kwargs['size'] == "1280*720"
            assert call_kwargs['duration'] == 5
            assert call_kwargs['prompt_extend'] == True
            assert call_kwargs['watermark'] == False
            assert 'negative_prompt' in call_kwargs
            
            # Verify returned URL
            assert video_url == "https://dashscope-result-sh.oss-cn-shanghai.aliyuncs.com/test_video.mp4"

    def test_generate_video_url_image_to_video_success(self, video_service, mock_video_response, tmp_path):
        """Test successful image-to-video URL generation with reference image."""
        test_prompt = "A continuation of previous scene"
        ref_img_path = tmp_path / "reference.jpg"
        ref_img_path.write_text("dummy image content")  # Create dummy file
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            video_url = video_service.generate_video_url(
                prompt=test_prompt,
                size=(1280, 720),
                duration=5,
                ref_img_path=str(ref_img_path)
            )
            
            # Verify API was called with correct parameters for image-to-video
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs
            
            assert call_kwargs['model'] == "wan2.6-i2v"
            assert call_kwargs['img_url'] == f"file://{os.path.abspath(ref_img_path)}"
            assert call_kwargs['shot_type'] == "multi"
            assert call_kwargs['prompt_extend'] == True
            assert call_kwargs['watermark'] == False

    def test_generate_video_url_image_to_video_nonexistent_file(self, video_service, tmp_path):
        """Test image-to-video with non-existent reference file falls back to text-to-video."""
        test_prompt = "Test prompt"
        non_existent_path = tmp_path / "nonexistent.jpg"
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_response = Mock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.output.video_url = "test_url"
            mock_call.return_value = mock_response
            
            video_url = video_service.generate_video_url(
                prompt=test_prompt,
                ref_img_path=str(non_existent_path)
            )
            
            # Should fall back to text-to-video model
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs['model'] == "wan2.6-t2v"
            assert 'img_url' not in call_kwargs

    def test_generate_video_url_quota_error(self, video_service):
        """Test video URL generation with quota error."""
        test_prompt = "Test prompt"
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.code = "AllocationQuota.FreeTierOnly"
        mock_response.message = "Free tier quota exhausted"
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_response
            
            with pytest.raises(RuntimeError, match="Aliyun Dashscope Quota Error"):
                video_service.generate_video_url(test_prompt)

    def test_generate_video_url_other_api_error(self, video_service):
        """Test video URL generation with other API error."""
        test_prompt = "Test prompt"
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.code = "InternalError"
        mock_response.message = "Internal server error"
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_response
            
            with pytest.raises(RuntimeError, match="Video generation failed"):
                video_service.generate_video_url(test_prompt)

    def test_generate_video_url_unsupported_provider(self):
        """Test video URL generation with unsupported provider."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            service = VideoService(api_provider="unsupported")
            
            with pytest.raises(ValueError, match="Unsupported provider"):
                service.generate_video_url("Test prompt")

    def test_generate_video_url_default_parameters(self, video_service, mock_video_response):
        """Test video URL generation with default parameters."""
        test_prompt = "Default test"

        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response

            video_url = video_service.generate_video_url(prompt=test_prompt)

            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs

            # Verify default values (updated to 1080p for higher quality)
            assert call_kwargs['size'] == "1920*1080"
            assert call_kwargs['duration'] == 5
            assert call_kwargs['prompt_extend'] == True
            assert call_kwargs['watermark'] == False

            assert video_url.startswith("https://")

    @pytest.mark.parametrize("size_param", [(640, 480), (1920, 1080), (1024, 768)])
    def test_different_video_sizes(self, size_param, video_service, mock_video_response):
        """Test video generation with different sizes."""
        test_prompt = f"Test size {size_param}"
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            video_url = video_service.generate_video_url(
                prompt=test_prompt,
                size=size_param
            )
            
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs['size'] == f"{size_param[0]}*{size_param[1]}"

    @pytest.mark.parametrize("duration_param", [3, 5, 10, 15])
    def test_different_video_durations(self, duration_param, video_service, mock_video_response):
        """Test video generation with different durations."""
        test_prompt = f"Test duration {duration_param}"
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            video_url = video_service.generate_video_url(
                prompt=test_prompt,
                duration=duration_param
            )
            
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs['duration'] == duration_param

    def test_generate_video_url_with_negative_prompt_text_to_video(self, video_service, mock_video_response):
        """Test text-to-video generation includes negative prompt."""
        test_prompt = "Test prompt"
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            video_service.generate_video_url(prompt=test_prompt)
            
            call_kwargs = mock_call.call_args.kwargs
            # Text-to-video should have negative_prompt
            assert 'negative_prompt' in call_kwargs
            assert "blurry" in call_kwargs['negative_prompt']
            assert "low quality" in call_kwargs['negative_prompt']

    def test_generate_video_url_no_negative_prompt_image_to_video(self, video_service, mock_video_response, tmp_path):
        """Test image-to-video generation includes negative prompt (updated behavior)."""
        test_prompt = "Test prompt"
        ref_img_path = tmp_path / "reference.jpg"
        ref_img_path.write_text("dummy")

        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response

            video_service.generate_video_url(
                prompt=test_prompt,
                ref_img_path=str(ref_img_path)
            )

            call_kwargs = mock_call.call_args.kwargs
            # Image-to-video should also have negative_prompt (updated behavior for better quality)
            assert 'negative_prompt' in call_kwargs
            assert "blurry" in call_kwargs['negative_prompt']
            assert "low quality" in call_kwargs['negative_prompt']

    def test_dashscope_base_url_set(self):
        """Test that dashscope base URL is set correctly."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            with patch('magicplay.services.video_api.dashscope.base_http_api_url', '') as mock_base_url:
                VideoService()
                # Should be set to Aliyun URL
                assert dashscope.base_http_api_url == "https://dashscope.aliyuncs.com/api/v1"

    def test_generate_video_url_empty_prompt(self, video_service, mock_video_response):
        """Test video generation with empty prompt."""
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            # Empty prompt should still work
            video_url = video_service.generate_video_url(prompt="")
            
            assert video_url.startswith("https://")

    def test_generate_video_url_long_prompt(self, video_service, mock_video_response):
        """Test video generation with long prompt."""
        long_prompt = "A" * 1000  # Very long prompt
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            video_url = video_service.generate_video_url(prompt=long_prompt)
            
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs['prompt'] == long_prompt

    def test_generate_video_url_with_shot_type(self, video_service, mock_video_response, tmp_path):
        """Test image-to-video generation includes shot_type parameter."""
        test_prompt = "Test prompt"
        ref_img_path = tmp_path / "reference.jpg"
        ref_img_path.write_text("dummy")
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            video_service.generate_video_url(
                prompt=test_prompt,
                ref_img_path=str(ref_img_path)
            )
            
            call_kwargs = mock_call.call_args.kwargs
            # Image-to-video should have shot_type parameter
            assert 'shot_type' in call_kwargs
            assert call_kwargs['shot_type'] == "multi"

    def test_generate_video_url_error_handling_various_status_codes(self, video_service):
        """Test video generation error handling for various status codes."""
        test_cases = [
            (403, "Forbidden", "Access denied"),
            (404, "NotFound", "Resource not found"),
            (429, "RateLimit", "Too many requests"),
            (502, "BadGateway", "Bad gateway"),
        ]
        
        for status_code, code, message in test_cases:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.code = code
            mock_response.message = message
            
            with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
                mock_call.return_value = mock_response
                
                with pytest.raises(RuntimeError, match="Video generation failed"):
                    video_service.generate_video_url("Test prompt")

    def test_generate_video_url_special_characters_in_prompt(self, video_service, mock_video_response):
        """Test video generation with special characters in prompt."""
        special_prompt = "Test with special chars: © ® ™ ∞ ≈ ≠ ≤ ≥ α β γ δ ε ζ η θ"
        
        with patch('magicplay.services.video_api.VideoSynthesis.call') as mock_call:
            mock_call.return_value = mock_video_response
            
            video_url = video_service.generate_video_url(prompt=special_prompt)
            
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs['prompt'] == special_prompt
            assert video_url.startswith("https://")