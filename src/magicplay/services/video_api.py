import os
import time
from http import HTTPStatus
from typing import Optional, Tuple

import dashscope
from dashscope import VideoSynthesis
from dotenv import load_dotenv

load_dotenv()


class VideoService:
    def __init__(
        self,
        api_provider: str = "qwen",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        self.api_provider = api_provider
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable is not set")

        dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    def generate_video_url(
        self,
        prompt: str,
        size: Tuple[int, int] = (
            1920,
            1080,
        ),  # Updated default to 1080p for higher quality
        duration: int = 5,
        ref_img_path: Optional[str] = None,
    ) -> str:
        """
        Call the video generation API and return the video URL.

        Enhanced for sci-fi/suspense genre optimization:
        - Higher resolution default (1920x1080)
        - Extended negative prompts for quality control
        - Optimized shot_type for dramatic scenes
        """
        if self.api_provider == "qwen":
            # Determine model based on input
            if ref_img_path and os.path.exists(ref_img_path):
                # Use Image-to-Video model
                model_name = "wan2.6-i2v"
                print(f"Using Image-to-Video model: {model_name} with reference image")

                img_url = f"file://{os.path.abspath(ref_img_path)}"

                # Enhanced negative prompt for sci-fi/suspense anime quality
                enhanced_negative_prompt = (
                    "blurry, low quality, watermark, text, distorted faces, extra limbs, "
                    "jittery, flickering, realistic, photographic, photorealistic, natural skin, "
                    "deformed hands, extra fingers, missing limbs, floating objects, "
                    "inconsistent lighting, color shifting, morphing artifacts, "
                    "unrealistic anatomy, defying gravity, impossible movements, "
                    "oversaturated, poor anime anatomy, unnatural pose, awkward framing"
                )

                # 添加重试机制
                return self._call_video_api_with_retry(
                    model_name=model_name,
                    prompt=prompt,
                    size=size,
                    duration=duration,
                    img_url=img_url,
                    negative_prompt=enhanced_negative_prompt,
                )
            else:
                # Use Text-to-Video model
                model_name = "wan2.6-t2v"

                # Enhanced negative prompt for sci-fi/suspense anime quality
                enhanced_negative_prompt = (
                    "blurry, low quality, watermark, text, distorted faces, extra limbs, "
                    "jittery, flickering, realistic, photographic, photorealistic, natural skin, "
                    "deformed hands, extra fingers, missing limbs, floating objects, "
                    "inconsistent lighting, color shifting, morphing artifacts, "
                    "unrealistic anatomy, defying gravity, impossible movements, "
                    "oversaturated, poor anime anatomy, unnatural pose, awkward framing"
                )

                return self._call_video_api_with_retry(
                    model_name=model_name,
                    prompt=prompt,
                    size=size,
                    duration=duration,
                    img_url=None,
                    negative_prompt=enhanced_negative_prompt,
                )
        else:
            raise ValueError(f"Unsupported provider: {self.api_provider}")

    def _call_video_api_with_retry(
        self,
        model_name: str,
        prompt: str,
        size: Tuple[int, int],
        duration: int,
        img_url: Optional[str] = None,
        negative_prompt: Optional[str] = None,
    ) -> str:
        """
        Call video API with retry logic for network errors.

        Args:
            model_name: Model to use (wan2.6-i2v or wan2.6-t2v)
            prompt: Visual prompt for generation
            size: Output video resolution (width, height)
            duration: Video duration in seconds
            img_url: Reference image URL for i2v mode
            negative_prompt: Negative prompt for quality control
        """
        last_exception = None

        # Use provided negative prompt or default
        if negative_prompt is None:
            negative_prompt = (
                "blurry, low quality, watermark, text, distorted faces, extra limbs, "
                "jittery, flickering, realistic, photographic, photorealistic, natural skin, "
                "deformed hands, extra fingers, missing limbs, floating objects, "
                "inconsistent lighting, color shifting, morphing artifacts"
            )

        for attempt in range(1, self.max_retries + 1):
            try:
                if img_url:
                    # Image-to-Video API call
                    rsp = VideoSynthesis.call(
                        api_key=self.api_key,
                        model=model_name,
                        duration=duration,
                        size=f"{size[0]}*{size[1]}",
                        prompt=prompt,
                        shot_type="multi",
                        img_url=img_url,
                        prompt_extend=True,
                        watermark=False,
                        negative_prompt=negative_prompt,
                    )
                else:
                    # Text-to-Video API call
                    rsp = VideoSynthesis.call(
                        api_key=self.api_key,
                        model=model_name,
                        prompt=prompt,
                        size=f"{size[0]}*{size[1]}",
                        duration=duration,
                        prompt_extend=True,
                        watermark=False,
                        negative_prompt=negative_prompt,
                    )

                if rsp.status_code == HTTPStatus.OK:
                    return rsp.output.video_url
                else:
                    if rsp.code == "AllocationQuota.FreeTierOnly":
                        raise RuntimeError(
                            "Aliyun Dashscope Quota Error: Your free tier quota for this model is exhausted. "
                            "Please go to the Aliyun Dashscope Console -> Model Plaza or API Keys management, "
                            "and disable the 'Use free tier only' option to switch to pay-as-you-go billing."
                        )
                    raise RuntimeError(
                        "Video generation failed, status_code: %s, code: %s, message: %s"
                        % (rsp.status_code, rsp.code, rsp.message)
                    )

            except Exception as e:
                last_exception = e
                error_msg = str(e)

                # 检查是否是网络相关错误
                is_network_error = any(
                    keyword in error_msg
                    for keyword in [
                        "HTTPSConnectionPool",
                        "NameResolutionError",
                        "timeout",
                        "connection",
                        "network",
                        "resolve",
                        "dashscope.aliyuncs.com",
                    ]
                )

                if attempt < self.max_retries and is_network_error:
                    print(f"Attempt {attempt}/{self.max_retries} failed with network error: {error_msg}")
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 1.5  # 指数退避
                else:
                    # 不是网络错误或者已经达到最大重试次数
                    if is_network_error and attempt == self.max_retries:
                        raise RuntimeError(
                            f"Video generation failed after {self.max_retries} retries "
                            f"due to network error: {error_msg}\n"
                            f"Please check your internet connection and DNS settings."
                        ) from e
                    else:
                        # 其他错误或非网络错误
                        raise RuntimeError(f"Video generation failed: {error_msg}") from e

        # 理论上不会到达这里，但为了完整性
        raise RuntimeError(f"Video generation failed after {self.max_retries} attempts") from last_exception
