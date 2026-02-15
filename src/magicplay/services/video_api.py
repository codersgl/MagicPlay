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
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable is not set")

        dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    def generate_video_url(
        self, prompt: str, size: Tuple[int, int] = (1280, 720), duration: int = 15
    ) -> str:
        """
        Call the video generation API and return the video URL.
        """
        if self.api_provider == "qwen":
            rsp = VideoSynthesis.call(
                api_key=self.api_key,
                model="wan2.6-t2v",
                prompt=prompt,
                size=f"{size[0]}*{size[1]}",
                duration=duration,
                shot_type="multi",
                prompt_extend=True,
                watermark=False,
            )

            if rsp.status_code == HTTPStatus.OK:
                return rsp.output.video_url
            else:
                raise RuntimeError(
                    "Video generation failed, status_code: %s, code: %s, message: %s"
                    % (rsp.status_code, rsp.code, rsp.message)
                )
        else:
            raise ValueError(f"Unsupported provider: {self.api_provider}")
