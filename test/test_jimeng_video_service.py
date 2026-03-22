"""
Pytest tests for JimengVideoService.
"""

from unittest.mock import Mock, patch

import pytest

from magicplay.services.jimeng_video_api import JimengVideoService


class TestJimengVideoService:
    """Test JimengVideoService functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.jimeng_access_key = "test_access_key"
        settings.jimeng_secret_key = "test_secret_key"
        settings.jimeng_api_base_url = "https://visual.volcengineapi.com"
        settings.jimeng_default_aspect_ratio = "16:9"
        return settings

    @pytest.fixture
    def service(self, mock_settings):
        """Create a JimengVideoService instance with mocked SDK."""
        with patch("magicplay.services.jimeng_video_api.VisualService"):
            svc = JimengVideoService(config=mock_settings)
            svc.service = Mock()  # Mock the SDK service
            return svc

    def test_service_initialization(self, mock_settings):
        """Test JimengVideoService initialization."""
        with patch("magicplay.services.jimeng_video_api.VisualService"):
            service = JimengVideoService(config=mock_settings)

            assert service.name == "jimeng_video"
            assert service.base_url == "https://visual.volcengineapi.com"
            assert service.default_aspect_ratio == "16:9"
            assert service.access_key == "test_access_key"
            assert service.secret_key == "test_secret_key"

    def test_service_initialization_missing_keys(self):
        """Test service initialization fails without API keys."""
        # Create mock settings without API keys
        mock_settings_no_keys = Mock()
        mock_settings_no_keys.jimeng_access_key = ""
        mock_settings_no_keys.jimeng_secret_key = ""
        mock_settings_no_keys.jimeng_api_base_url = "https://visual.volcengineapi.com"
        mock_settings_no_keys.jimeng_default_aspect_ratio = "16:9"

        with pytest.raises(
            ValueError,
            match="JIMENG_ACCESS_KEY and JIMENG_SECRET_KEY are required",
        ):
            with patch("magicplay.services.jimeng_video_api.VisualService"):
                JimengVideoService(config=mock_settings_no_keys)

    def test_convert_duration_to_frames(self, service):
        """Test duration to frames conversion."""
        assert service._convert_duration_to_frames(5) == 121
        assert service._convert_duration_to_frames(10) == 241

    def test_convert_duration_to_frames_unsupported(self, service):
        """Test unsupported duration defaults to 5 seconds."""
        assert service._convert_duration_to_frames(3) == 121  # defaults to 5s

    def test_submit_task_t2v(self, service):
        """Test text-to-video task submission."""
        # Mock the SDK method
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 10000,
            "data": {"task_id": "test_task_123"},
        }
        service.service.cv_sync2async_submit_task.return_value = mock_response

        task_id = service._submit_task(
            req_key=service.REQ_KEY_T2V,
            prompt="A cat walking",
            seed=-1,
            frames=121,
            aspect_ratio="16:9",
        )

        assert task_id == "test_task_123"
        service.service.cv_sync2async_submit_task.assert_called_once()

    def test_query_task_status(self, service):
        """Test task status query."""
        # Mock the SDK method
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 10000,
            "data": {
                "status": "done",
                "video_url": "https://example.com/video.mp4",
            },
        }
        service.service.cv_sync2async_get_result.return_value = mock_response

        result = service._query_task(service.REQ_KEY_T2V, "test_task_123")

        assert result["data"]["status"] == "done"
        assert result["data"]["video_url"] == "https://example.com/video.mp4"

    def test_submit_task_error(self, service):
        """Test task submission handles API errors."""
        # Mock error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 50413,
            "message": "Post Text Risk Not Pass",
        }
        service.service.cv_sync2async_submit_task.return_value = mock_response

        with pytest.raises(RuntimeError, match="Jimeng API error"):
            service._submit_task(
                req_key=service.REQ_KEY_T2V,
                prompt="A cat walking",
                seed=-1,
                frames=121,
                aspect_ratio="16:9",
            )

    def test_wait_for_task_success(self, service):
        """Test waiting for task completion."""
        service.poll_interval = 0.1  # Fast polling for test

        # Mock the SDK method
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 10000,
            "data": {
                "status": "done",
                "video_url": "https://example.com/video.mp4",
            },
        }
        service.service.cv_sync2async_get_result.return_value = mock_response

        video_url = service._wait_for_task(service.REQ_KEY_T2V, "test_task_123")

        assert video_url == "https://example.com/video.mp4"

    def test_wait_for_task_timeout(self, service):
        """Test task timeout."""
        service.poll_interval = 0.1
        service.timeout = 0.3  # Short timeout

        # Mock the SDK method to always return generating
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 10000,
            "data": {"status": "generating"},
        }
        service.service.cv_sync2async_get_result.return_value = mock_response

        with pytest.raises(RuntimeError, match="timed out"):
            service._wait_for_task(service.REQ_KEY_T2V, "test_task_123")

    def test_supported_aspect_ratios(self, service):
        """Test supported aspect ratios."""
        for ratio in ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9"]:
            assert ratio in service.SUPPORTED_ASPECT_RATIOS

    def test_supported_durations(self, service):
        """Test supported durations."""
        assert 5 in service.SUPPORTED_DURATIONS
        assert 10 in service.SUPPORTED_DURATIONS
