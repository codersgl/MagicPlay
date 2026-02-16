import os
from http import HTTPStatus
from typing import Tuple, Dict, Any

import dashscope
from dashscope import VideoSynthesis
from dotenv import load_dotenv

load_dotenv()


class VideoService:
    def __init__(
        self,
        api_provider: str = "qwen",
    ) -> None:
        self.api_provider = api_provider
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable is not set")

        dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    def generate_video_url(
        self,
        prompt: str,
        size: Tuple[int, int] = (1280, 720),
        duration: int = 5,
        ref_img_path: str = None,
    ) -> str:
        """
        Call the video generation API and return the video URL.
        """
        if self.api_provider == "qwen":
            # Determine model based on input
            if ref_img_path and os.path.exists(ref_img_path):
                # Use Image-to-Video model
                model_name = "wan2.6-i2v"
                print(f"Using Image-to-Video model: {model_name} with reference image")

                img_url = f"file://{os.path.abspath(ref_img_path)}"

                rsp = VideoSynthesis.call(
                    api_key=self.api_key,
                    model=model_name,
                    # Duration: Wan2.6 favors 5s but supports extension. 5s is default/safe.
                    duration=duration,
                    # Resolution: 720P (1280x720) or 1080P/480P.
                    size=f"{size[0]}*{size[1]}",
                    prompt=prompt,
                    shot_type="multi",
                    img_url=img_url,
                    prompt_extend=True,
                    watermark=False,
                )
            else:
                # Use Text-to-Video model
                # Keeping user's original preference if possible, but user code said wan2.6-t2v
                model_name = "wan2.6-t2v"

                rsp = VideoSynthesis.call(
                    api_key=self.api_key,
                    model=model_name,
                    prompt=prompt,
                    size=f"{size[0]}*{size[1]}",
                    duration=duration,
                    prompt_extend=True,
                    watermark=False,
                    negative_prompt="blurry, low quality, watermark, text, distorted faces, extra limbs, jittery, flickering",
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
        else:
            raise ValueError(f"Unsupported provider: {self.api_provider}")
