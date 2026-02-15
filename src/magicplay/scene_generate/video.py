import os
import time
from http import HTTPStatus
from pathlib import Path
from typing import Optional, Tuple, Union

import dashscope
from dashscope import VideoSynthesis

from magicplay.utils import Utils


class VideoGenerator:
    def __init__(
        self,
        api_provider: str = "qwen",
        scene_source: Optional[Union[str, Path]] = None,
        save_path: Optional[Union[str, Path]] = None,
        size: Tuple[int, int] = (1280, 720),
        duration: int = 15,
    ) -> None:
        self.api_provider = api_provider
        self.size = size
        self.duration = duration
        if scene_source is None:
            self.scene_source = Path(__file__).parent.parent / "scenes"
        else:
            self.scene_source = Path(scene_source)

        if save_path is None:
            self.save_dir = Path("videos")
        else:
            self.save_dir = Path(save_path)

        # Ensure save directory exists
        self.save_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.prompt = Utils.get_prompt(self.scene_source)
        except Exception as e:
            print(f"Warning: Could not load prompt from {self.scene_source}: {e}")
            self.prompt = ""

    def generate_video(self):
        if not self.prompt:
            raise ValueError(
                f"No prompt loaded from {self.scene_source}. Cannot generate video."
            )

        if self.api_provider == "qwen":
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
            print("Please wait while video is being generated...")
            api_key = os.environ.get("DASHSCOPE_API_KEY", "")
            if not api_key:
                raise ValueError("DASHSCOPE_API_KEY environment variable is not set")

            rsp = VideoSynthesis.call(
                api_key=api_key,
                model="wan2.6-t2v",
                prompt=self.prompt,
                size=f"{self.size[0]}*{self.size[1]}",
                duration=self.duration,
                shot_type="multi",
                prompt_extend=True,
                watermark=True,
            )

            if rsp.status_code == HTTPStatus.OK:
                timestamp = int(time.time())
                output_path = self.save_dir / f"video_{timestamp}.mp4"
                if Utils.download_video(rsp.output.video_url, output_path):
                    print(f"Video saved to: {output_path}")
                    return output_path
                else:
                    raise RuntimeError("Failed to download generated video")
            else:
                raise RuntimeError(
                    "Video generation failed, status_code: %s, code: %s, message: %s"
                    % (rsp.status_code, rsp.code, rsp.message)
                )
