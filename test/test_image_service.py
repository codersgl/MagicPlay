"""
Pytest tests for ImageService.
"""

import os
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from magicplay.services.image_api import ImageService


class TestImageService:
    """Test ImageService functionality."""

    @pytest.fixture
    def image_service(self):
        """Create an ImageService instance for tests."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_api_key"}):
            return ImageService(api_provider="qwen")

    @pytest.fixture
    def mock_dashscope_response(self):
        """Create a mock DashScope response for successful image generation."""
        # Create a mock response that mimics the actual API response structure
        response = Mock()
        response.status_code = HTTPStatus.OK
        response.code = ""
        response.message = ""

        # Create mock output structure
        output_mock = Mock()
        choice_mock = Mock()
        message_mock = Mock()

        # Mock the content structure
        content_item = {
            "type": "image",
            "image": "https://dashscope-result-sh.oss-cn-shanghai.aliyuncs.com/test_image.jpg",
        }
        message_mock.content = [content_item]
        choice_mock.message = message_mock
        output_mock.choices = [choice_mock]

        response.output = output_mock
        return response

    def test_image_service_initialization_missing_api_key(self):
        """Test ImageService initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("magicplay.config.settings.load_dotenv") as mock_load_dotenv:
                with pytest.raises(
                    ValueError,
                    match="DASHSCOPE_API_KEY environment variable is not set",
                ):
                    ImageService(api_provider="qwen")

    def test_image_service_initialization_with_api_key(self):
        """Test ImageService initialization with API key."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            service = ImageService(api_provider="qwen")
            assert service.api_provider == "qwen"
            assert service.api_key == "test_key"

    def test_image_service_initialization_custom_provider(self):
        """Test ImageService initialization with custom provider."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Currently only "qwen" provider is supported
            service = ImageService(api_provider="qwen")
            assert service.api_provider == "qwen"

    def test_generate_image_url_success(self, image_service, mock_dashscope_response):
        """Test successful image URL generation."""
        test_prompt = "A beautiful landscape with mountains"

        with patch("dashscope.aigc.image_generation.ImageGeneration.call") as mock_call:
            mock_call.return_value = mock_dashscope_response

            image_url = image_service.generate_image_url(
                prompt=test_prompt,
                size=(1280, 720),
                negative_prompt="blurry, low quality",
                n=1,
                prompt_extend=True,
                watermark=False,
                seed=12345,
            )

            # Verify API was called with correct parameters
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs

            assert call_kwargs["api_key"] == "test_api_key"
            assert call_kwargs["model"] == "wan2.6-t2i"
            assert len(call_kwargs["messages"]) == 1
            assert call_kwargs["messages"][0].role == "user"
            assert call_kwargs["messages"][0].content[0]["text"] == test_prompt
            assert call_kwargs["negative_prompt"] == "blurry, low quality"
            assert call_kwargs["size"] == "1280*720"
            assert call_kwargs["n"] == 1
            assert call_kwargs["prompt_extend"] == True
            assert call_kwargs["watermark"] == False
            assert call_kwargs["seed"] == 12345

            # Verify returned URL
            assert (
                image_url
                == "https://dashscope-result-sh.oss-cn-shanghai.aliyuncs.com/test_image.jpg"
            )

    def test_generate_image_url_no_image_in_response(self, image_service):
        """Test image URL generation when response doesn't contain image."""
        test_prompt = "Test prompt"

        # Create a response without image content
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.OK
        output_mock = Mock()
        choice_mock = Mock()
        message_mock = Mock()
        message_mock.content = []  # Empty content
        choice_mock.message = message_mock
        output_mock.choices = [choice_mock]
        mock_response.output = output_mock

        with patch("dashscope.aigc.image_generation.ImageGeneration.call") as mock_call:
            mock_call.return_value = mock_response

            with pytest.raises(
                RuntimeError, match="No image URL found in API response"
            ):
                image_service.generate_image_url(test_prompt)

    def test_generate_image_url_quota_error(self, image_service):
        """Test image URL generation with quota error."""
        test_prompt = "Test prompt"

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.code = "AllocationQuota.FreeTierOnly"
        mock_response.message = "Free tier quota exhausted"

        with patch("dashscope.aigc.image_generation.ImageGeneration.call") as mock_call:
            mock_call.return_value = mock_response

            with pytest.raises(RuntimeError, match="Aliyun Dashscope Quota Error"):
                image_service.generate_image_url(test_prompt)

    def test_generate_image_url_other_api_error(self, image_service):
        """Test image URL generation with other API error."""
        test_prompt = "Test prompt"

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.code = "InternalError"
        mock_response.message = "Internal server error"

        with patch("dashscope.aigc.image_generation.ImageGeneration.call") as mock_call:
            mock_call.return_value = mock_response

            with pytest.raises(RuntimeError, match="Image generation failed"):
                image_service.generate_image_url(test_prompt)

    def test_generate_image_url_unsupported_provider(self):
        """Test image URL generation with unsupported provider."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            with pytest.raises(ValueError, match="Unsupported image provider"):
                ImageService(api_provider="unsupported")

    def test_generate_image_and_download_success(
        self, image_service, mock_dashscope_response, tmp_path
    ):
        """Test successful image generation and download."""
        test_prompt = "A beautiful sunset"
        output_path = tmp_path / "test_image.png"

        with (
            patch(
                "dashscope.aigc.image_generation.ImageGeneration.call"
            ) as mock_api_call,
            patch("requests.get") as mock_requests_get,
        ):

            mock_api_call.return_value = mock_dashscope_response

            # Mock successful download
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.iter_content = Mock(return_value=[b"fake_image_data"])
            mock_requests_get.return_value = mock_response

            result_path = image_service.generate_image_and_download(
                prompt=test_prompt,
                output_path=str(output_path),
                size=(1024, 768),
                negative_prompt="watermark, text",
                n=2,
                prompt_extend=False,
                watermark=True,
                seed=999,
            )

            # Verify API call
            mock_api_call.assert_called_once()
            call_kwargs = mock_api_call.call_args.kwargs
            assert call_kwargs["size"] == "1024*768"
            assert call_kwargs["negative_prompt"] == "watermark, text"
            assert call_kwargs["n"] == 2
            assert call_kwargs["prompt_extend"] == False
            assert call_kwargs["watermark"] == True
            assert call_kwargs["seed"] == 999

            # Verify download call
            mock_requests_get.assert_called_once_with(
                "https://dashscope-result-sh.oss-cn-shanghai.aliyuncs.com/test_image.jpg",
                stream=True,
                timeout=30,
            )

            # Verify result
            assert result_path == str(output_path)
            assert output_path.parent.exists()  # Directory was created
            assert output_path.exists()  # File was created

    def test_generate_image_and_download_creates_directory(
        self, image_service, mock_dashscope_response, tmp_path
    ):
        """Test that download creates output directory if it doesn't exist."""
        test_prompt = "Test prompt"
        output_dir = tmp_path / "nested" / "deep" / "directory"
        output_path = output_dir / "test_image.jpg"

        assert not output_dir.exists()

        with (
            patch(
                "dashscope.aigc.image_generation.ImageGeneration.call"
            ) as mock_api_call,
            patch("requests.get") as mock_requests_get,
        ):

            mock_api_call.return_value = mock_dashscope_response
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.iter_content = Mock(return_value=[b"fake_data"])
            mock_requests_get.return_value = mock_response

            result_path = image_service.generate_image_and_download(
                prompt=test_prompt, output_path=str(output_path)
            )

            assert output_dir.exists()
            assert result_path == str(output_path)

    def test_generate_image_and_download_download_failure(
        self, image_service, mock_dashscope_response, tmp_path
    ):
        """Test image generation with download failure."""
        test_prompt = "Test prompt"
        output_path = tmp_path / "test_image.png"

        with (
            patch(
                "dashscope.aigc.image_generation.ImageGeneration.call"
            ) as mock_api_call,
            patch("requests.get") as mock_requests_get,
        ):

            mock_api_call.return_value = mock_dashscope_response
            mock_requests_get.side_effect = Exception("Network error")

            with pytest.raises(RuntimeError, match="Failed to download image"):
                image_service.generate_image_and_download(
                    prompt=test_prompt, output_path=str(output_path)
                )

    def test_generate_image_and_download_api_failure(self, image_service, tmp_path):
        """Test image generation when API fails."""
        test_prompt = "Test prompt"
        output_path = tmp_path / "test_image.png"

        with patch(
            "dashscope.aigc.image_generation.ImageGeneration.call"
        ) as mock_api_call:
            mock_api_call.side_effect = RuntimeError("API error")

            # The actual error message will come from generate_image_and_download
            # which wraps the API error in a RuntimeError with "Failed to download image"
            with pytest.raises(RuntimeError):
                image_service.generate_image_and_download(
                    prompt=test_prompt, output_path=str(output_path)
                )

    def test_generate_image_url_default_parameters(
        self, image_service, mock_dashscope_response
    ):
        """Test image URL generation with default parameters."""
        test_prompt = "Default test"

        with patch("dashscope.aigc.image_generation.ImageGeneration.call") as mock_call:
            mock_call.return_value = mock_dashscope_response

            image_url = image_service.generate_image_url(prompt=test_prompt)

            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs

            # Verify default values
            assert call_kwargs["size"] == "1280*720"
            assert call_kwargs["negative_prompt"] == ""
            assert call_kwargs["n"] == 1
            assert call_kwargs["prompt_extend"] == True
            assert call_kwargs["watermark"] == False
            assert "seed" not in call_kwargs  # seed should not be included when None

            assert image_url.startswith("https://")

    def test_multiple_images_parameter(self, image_service, mock_dashscope_response):
        """Test image generation with multiple images parameter."""
        test_prompt = "Multiple images"

        with patch("dashscope.aigc.image_generation.ImageGeneration.call") as mock_call:
            mock_call.return_value = mock_dashscope_response

            # Even when n > 1, we should still get the first image URL
            image_url = image_service.generate_image_url(
                prompt=test_prompt, n=4  # Request 4 images
            )

            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs["n"] == 4

            # Should still return a valid URL
            assert image_url.startswith("https://")

    @pytest.mark.parametrize("size_param", [(640, 480), (1920, 1080), (512, 512)])
    def test_different_image_sizes(
        self, size_param, image_service, mock_dashscope_response
    ):
        """Test image generation with different sizes."""
        test_prompt = f"Test size {size_param}"

        with patch("dashscope.aigc.image_generation.ImageGeneration.call") as mock_call:
            mock_call.return_value = mock_dashscope_response

            image_url = image_service.generate_image_url(
                prompt=test_prompt, size=size_param
            )

            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs["size"] == f"{size_param[0]}*{size_param[1]}"

    def test_seed_parameter_handling(self, image_service, mock_dashscope_response):
        """Test that seed parameter is properly handled."""
        test_prompt = "Seeded generation"

        with patch("dashscope.aigc.image_generation.ImageGeneration.call") as mock_call:
            mock_call.return_value = mock_dashscope_response

            # Test with seed
            image_service.generate_image_url(prompt=test_prompt, seed=424242)

            call_kwargs_with_seed = mock_call.call_args.kwargs
            assert call_kwargs_with_seed["seed"] == 424242

            # Reset mock
            mock_call.reset_mock()
            mock_call.return_value = mock_dashscope_response

            # Test without seed (should not include seed parameter)
            image_service.generate_image_url(prompt=test_prompt)

            call_kwargs_no_seed = mock_call.call_args.kwargs
            assert "seed" not in call_kwargs_no_seed
