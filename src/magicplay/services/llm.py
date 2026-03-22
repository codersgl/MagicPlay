"""
LLM Service - DeepSeek Integration

Large Language Model service using DeepSeek API.
"""

from typing import Any, Dict, Optional

from loguru import logger
from openai import OpenAI

from magicplay.config import Settings
from magicplay.exceptions import APIError, ConfigurationError
from magicplay.ports.services import ILLMService
from magicplay.services.base import BaseService
from magicplay.utils.retry import api_retry


class LLMService(BaseService, ILLMService):
    """
    DeepSeek LLM service implementation.

    Provides text generation capabilities using DeepSeek's chat models.

    Features:
    - Configurable temperature and max tokens
    - Automatic retry with exponential backoff
    - Health check support
    - Structured logging
    """

    name = "deepseek"
    version = "1.0.0"

    def __init__(self, config: Optional[Settings] = None):
        """
        Initialize DeepSeek LLM service.

        Args:
            config: Application settings (uses global config if not provided)
        """
        if config is None:
            from magicplay.config import get_settings

            config = get_settings()

        super().__init__(config)

        # Validate configuration
        if not config.deepseek_api_key:
            raise ConfigurationError(
                "DeepSeek API key is required", setting_name="deepseek_api_key"
            )

        # Initialize OpenAI-compatible client
        self.client = OpenAI(
            api_key=config.deepseek_api_key,
            base_url=config.deepseek_base_url,
        )
        self.model = config.deepseek_model
        self.default_temperature = config.default_temperature
        self.max_retries = config.max_retry_attempts

        self.logger = logger

    def _get_api_key(self) -> str:
        """Get API key from configuration."""
        return self.config.deepseek_api_key

    @api_retry(max_attempts=3)
    def generate_content(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Generate content using DeepSeek API.

        Args:
            system_prompt: System instruction context
            user_prompt: User's request/prompt
            temperature: Creativity parameter (0.0-2.0, default from config)
            max_tokens: Maximum tokens in response
            **kwargs: Additional OpenAI API parameters

        Returns:
            Generated text content

        Raises:
            APIError: If API call fails
        """
        temp = temperature if temperature is not None else self.default_temperature

        # Validate temperature
        if not (0.0 <= temp <= 2.0):
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temp}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Build API parameters
        api_params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            "stream": False,
        }

        if max_tokens:
            api_params["max_tokens"] = max_tokens

        # Add any additional parameters
        api_params.update(kwargs)

        try:
            self._log_request(
                "chat/completions",
                {
                    "model": self.model,
                    "temperature": temp,
                    "message_count": len(messages),
                },
            )

            response = self.client.chat.completions.create(**api_params)

            if not response.choices or len(response.choices) == 0:
                self._raise_api_error("No response generated from DeepSeek API")

            content = response.choices[0].message.content

            self._log_response(
                "chat/completions",
                200,
                {
                    "content_length": len(content) if content else 0,
                    "usage": dict(response.usage) if response.usage else {},
                },
            )

            return content or ""

        except APIError:
            # Re-raise our own errors
            raise
        except Exception as e:
            self.logger.error(f"DeepSeek API call failed: {e}")
            self._raise_api_error(
                message=f"DeepSeek API call failed: {e}", response_body=str(e)
            )

    def health_check(self) -> bool:
        """
        Check if DeepSeek API is accessible.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Simple test prompt
            self.generate_content(
                system_prompt="You are a test assistant.",
                user_prompt="Respond with just 'OK'",
                temperature=0,
                max_tokens=5,
            )
            self._healthy = True
            self.logger.info("DeepSeek health check passed")
            return True

        except Exception as e:
            self.logger.error(f"DeepSeek health check failed: {e}")
            self._healthy = False
            return False

    def __repr__(self) -> str:
        return f"LLMService(model={self.model}, healthy={self._healthy})"
