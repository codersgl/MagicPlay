"""
Pytest tests for LLMService.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from magicplay.services.llm import LLMService


class TestLLMService:
    """Test LLMService functionality."""

    @pytest.mark.skip(reason="Requires special environment mocking")
    def test_llm_service_initialization_missing_api_key(self):
        """Test LLMService initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("magicplay.config.settings.load_dotenv"):
                with pytest.raises(
                    ValueError,
                    match="DEEPSEEK_API_KEY environment variable is not set",
                ):
                    LLMService()

    def test_llm_service_initialization_with_api_key(self):
        """Test LLMService initialization with API key."""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            with patch("magicplay.config.settings.load_dotenv"):
                service = LLMService()
                assert service.client is not None

    @pytest.fixture
    def llm_service(self):
        """Create an LLMService instance for tests."""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_api_key"}):
            return LLMService()

    def test_generate_content_success(self, llm_service):
        """Test successful content generation."""
        system_prompt = "You are a helpful assistant."
        user_prompt = "Hello, how are you?"

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "I'm fine, thank you!"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch.object(llm_service.client.chat.completions, "create") as mock_create:
            mock_create.return_value = mock_response

            result = llm_service.generate_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=1.3,
            )

            # Verify API call
            mock_create.assert_called_once()
            call_args = mock_create.call_args

            assert call_args.kwargs["model"] == "deepseek-chat"
            assert call_args.kwargs["temperature"] == 1.3
            assert not call_args.kwargs.get("stream", False)

            messages = call_args.kwargs["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == system_prompt
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == user_prompt

            # Verify result
            assert result == "I'm fine, thank you!"

    def test_generate_content_with_custom_temperature(self, llm_service):
        """Test content generation with custom temperature."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Test response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch.object(llm_service.client.chat.completions, "create") as mock_create:
            mock_create.return_value = mock_response

            llm_service.generate_content(
                system_prompt="Test system",
                user_prompt="Test user",
                temperature=0.8,
            )

            call_args = mock_create.call_args
            assert call_args.kwargs["temperature"] == 0.8

    def test_generate_content_api_exception(self, llm_service):
        """Test content generation when API raises exception."""
        with patch.object(llm_service.client.chat.completions, "create") as mock_create:
            mock_create.side_effect = Exception("API connection failed")

            from magicplay.exceptions import APIError

            with pytest.raises(APIError, match="DeepSeek API call failed"):
                llm_service.generate_content(system_prompt="Test", user_prompt="Test")

    def test_generate_content_empty_response(self, llm_service):
        """Test content generation with empty response."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = ""  # Empty content
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch.object(llm_service.client.chat.completions, "create") as mock_create:
            mock_create.return_value = mock_response

            result = llm_service.generate_content(system_prompt="Test", user_prompt="Test")

            assert result == ""  # Should handle empty string response

    def test_base_url_configuration(self):
        """Test that base_url is correctly configured."""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            service = LLMService()

            # Check that client is configured with DeepSeek base URL
            assert service.client.base_url == "https://api.deepseek.com"

            # Verify the client is an OpenAI client instance
            assert service.client.__class__.__name__ == "OpenAI"

    def test_generate_content_with_different_prompts(self, llm_service):
        """Test content generation with various prompt lengths."""
        test_cases = [
            ("Short system", "Short user"),
            (
                "Long system prompt with multiple sentences and details",
                "Short user",
            ),
            (
                "Short system",
                "Long user prompt with many words and complex instructions",
            ),
            ("System", "User"),
        ]

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch.object(llm_service.client.chat.completions, "create") as mock_create:
            mock_create.return_value = mock_response

            for system_prompt, user_prompt in test_cases:
                result = llm_service.generate_content(system_prompt=system_prompt, user_prompt=user_prompt)

                # Should not raise any exception
                assert result == "Response"
