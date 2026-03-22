import os
import ssl
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any, Optional, Tuple

import dashscope
import requests
import tenacity
from dashscope.aigc.image_generation import ImageGeneration
from dashscope.api_entities.dashscope_response import Message
from dotenv import load_dotenv

load_dotenv()

# Define retry decorator for network-related errors
def retry_on_network_error(func):
    """Retry decorator for network-related errors with exponential backoff."""
    retry_decorator = tenacity.retry(
        retry=tenacity.retry_if_exception_type(
            (
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
                ssl.SSLError,
                OSError,  # General OS-level errors
            )
        ),
        stop=tenacity.stop_after_attempt(5),  # Max 5 attempts
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=30),  # Exponential backoff: 2, 4, 8, 16, 30 seconds
        before_sleep=lambda retry_state: print(
            f"Retrying {func.__name__} due to network error, "
            f"attempt {retry_state.attempt_number}/{5}, "
            f"waiting {retry_state.next_action.sleep if hasattr(retry_state.next_action, 'sleep') else 2} seconds..."
        ) if retry_state.attempt_number > 0 else None,
        reraise=True,
    )
    return retry_decorator(func)


class ImageService:
    SUPPORTED_PROVIDERS = ["qwen", "jimeng"]

    def __init__(
        self,
        api_provider: Optional[str] = None,
        config: Optional[Any] = None,
    ) -> None:
        # Get default provider from settings if not specified
        if api_provider is None:
            from magicplay.config import get_settings
            settings = get_settings()
            api_provider = settings.default_image_provider

        if api_provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported image provider: {api_provider}. "
                f"Supported: {self.SUPPORTED_PROVIDERS}"
            )

        self.api_provider = api_provider
        self.config = config

        if api_provider == "qwen":
            self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
            if not self.api_key:
                raise ValueError("DASHSCOPE_API_KEY environment variable is not set")
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

        elif api_provider == "jimeng":
            from magicplay.services.jimeng_video_api import JimengVideoService
            if config is None:
                from magicplay.config import get_settings
                config = get_settings()
            self.jimeng_service = JimengVideoService(config=config)

    def _get_api_response(self, rsp):
        """
        Handle the API response which could be either a direct response or a generator.
        Returns the response object.
        """
        import inspect
        
        # Check if response is a generator
        if inspect.isgenerator(rsp):
            try:
                # Get the first (and typically only) response from the generator
                return next(rsp)
            except StopIteration:
                raise RuntimeError("Image generation API returned empty generator")
        # Otherwise, assume it's a direct response object
        return rsp

    @retry_on_network_error
    def generate_image_url(
        self,
        prompt: str,
        size: Tuple[int, int] = (1280, 720),
        negative_prompt: str = "",
        n: int = 1,
        prompt_extend: bool = True,
        watermark: bool = False,
        seed: Optional[int] = None,
    ) -> str:
        """
        Call the text-to-image API and return the image URL.
        Returns the first image URL when n > 1.
        """
        if self.api_provider == "qwen":
            # Use wan2.6-t2i model for text-to-image generation
            model_name = "wan2.6-t2i"
            print(f"Using Text-to-Image model: {model_name}")

            # Create message as required by the API
            message = Message(role="user", content=[{"text": prompt}])

            # Prepare parameters
            size_str = f"{size[0]}*{size[1]}"
            params = {
                "negative_prompt": negative_prompt,
                "size": size_str,
                "n": n,
                "prompt_extend": prompt_extend,
                "watermark": watermark,
            }
            if seed is not None:
                params["seed"] = seed

            try:
                api_result = ImageGeneration.call(
                    api_key=self.api_key, model=model_name, messages=[message], **params
                )
                
                # Handle the response (could be generator or direct response)
                rsp = self._get_api_response(api_result)

                if rsp.status_code == HTTPStatus.OK:
                    # Extract the first image URL from the response
                    if (
                        hasattr(rsp, "output")
                        and rsp.output
                        and hasattr(rsp.output, "choices")
                    ):
                        choice = rsp.output.choices[0]
                        if (
                            hasattr(choice, "message")
                            and choice.message
                            and hasattr(choice.message, "content")
                        ):
                            for content_item in choice.message.content:
                                if (
                                    isinstance(content_item, dict)
                                    and content_item.get("type") == "image"
                                ):
                                    return content_item.get("image", "")

                    raise RuntimeError("No image URL found in API response")
                else:
                    if hasattr(rsp, "code") and rsp.code == "AllocationQuota.FreeTierOnly":
                        raise RuntimeError(
                            "Aliyun Dashscope Quota Error: Your free tier quota for this model is exhausted. "
                            "Please go to the Aliyun Dashscope Console -> Model Plaza or API Keys management, "
                            "and disable the 'Use free tier only' option to switch to pay-as-go billing."
                        )
                    raise RuntimeError(
                        "Image generation failed, status_code: %s, code: %s, message: %s"
                        % (rsp.status_code, rsp.code, rsp.message)
                    )
            except Exception as e:
                # Re-raise any exceptions that should trigger retry
                if isinstance(e, (requests.exceptions.SSLError, 
                                requests.exceptions.ConnectionError,
                                requests.exceptions.Timeout,
                                ssl.SSLError, OSError)):
                    raise
                # For other exceptions (API errors, quota errors), don't retry
                raise RuntimeError(f"Image generation API error: {e}")
        else:
            raise ValueError(f"Unsupported provider: {self.api_provider}")

    def generate_image_and_download(
        self,
        prompt: str,
        output_path: str,
        size: Tuple[int, int] = (1280, 720),
        negative_prompt: str = "",
        n: int = 1,
        prompt_extend: bool = True,
        watermark: bool = False,
        seed: Optional[int] = None,
    ) -> str:
        """
        Generate an image and download it directly to the specified path.
        Returns the path to the downloaded image.
        """
        if self.api_provider == "jimeng":
            # Use Jimeng T2I API (handles generation and download internally)
            result = self.jimeng_service.generate_image(
                prompt=prompt,
                output_path=output_path,
                negative_prompt=negative_prompt,
                width=size[0],
                height=size[1],
                seed=seed if seed is not None else -1,
            )
            if result is None:
                raise RuntimeError("Jimeng image generation failed")
            return str(result)

        # Generate image URL for Qwen provider
        image_url = self.generate_image_url(
            prompt=prompt,
            size=size,
            negative_prompt=negative_prompt,
            n=n,
            prompt_extend=prompt_extend,
            watermark=watermark,
            seed=seed,
        )

        # Download the image
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(output_path_obj, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"Image downloaded to: {output_path_obj}")
            return str(output_path_obj)
        except Exception as e:
            raise RuntimeError(f"Failed to download image: {e}")
