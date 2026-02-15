from pathlib import Path
from typing import Tuple, Union

from magicplay.services.video_api import VideoService
from magicplay.utils.media import MediaUtils


class VideoGenerator:
    def __init__(
        self,
        api_provider: str = "qwen",
        size: Tuple[int, int] = (1280, 720),
        duration: int = 15,
    ) -> None:
        self.service = VideoService(api_provider=api_provider)
        self.size = size
        self.duration = duration

    def generate_video(self, visual_prompt: str, output_path: Union[str, Path]) -> Path:
        """
        Generate a video from a visual prompt string.
        """
        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Generating video to {output_path}...")

        try:
            video_url = self.service.generate_video_url(
                prompt=visual_prompt, size=self.size, duration=self.duration
            )

            if MediaUtils.download_video(video_url, output_path):
                print(f"Video saved to: {output_path}")
                return output_path
            else:
                raise RuntimeError("Failed to download generated video")

        except Exception as e:
            raise RuntimeError(f"Video generation failed: {e}")
