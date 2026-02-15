from typing import List, Union
from pathlib import Path
import requests
from tqdm import tqdm

try:
    from moviepy import VideoFileClip, concatenate_videoclips

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print(
        "Warning: moviepy not installed or import error. Video stitching will be skipped."
    )


class MediaUtils:
    @staticmethod
    def download_video(url: str, save_path: str | Path):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "wb") as f:
                if total_size == 0:
                    f.write(response.content)
                    print(f"Download complete: {save_path.name}")
                else:
                    with tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        desc=save_path.name,
                        unit_divisor=1024,
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
            return True

        except requests.exceptions.RequestException as e:
            print(f"Download failed: {e}")
            raise

    @staticmethod
    def stitch_videos(video_files: List[str], output_path: Union[str, Path]):
        output_path = Path(output_path)
        if not MOVIEPY_AVAILABLE:
            print("Skipping stitching: moviepy not available.")
            return

        print("Stitching videos...")
        try:
            clips = [VideoFileClip(f) for f in video_files]
            if not clips:
                return

            final_clip = concatenate_videoclips(clips)

            output_path.parent.mkdir(parents=True, exist_ok=True)

            final_clip.write_videofile(
                str(output_path), codec="libx264", audio_codec="aac", logger=None
            )
            print(f"Full episode video saved: {output_path}")

            # Close clips
            for clip in clips:
                clip.close()
            final_clip.close()

        except Exception as e:
            print(f"Error during stitching: {e}")
            raise
