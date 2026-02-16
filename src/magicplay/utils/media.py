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
    def extract_last_frame(
        video_path: str | Path, output_image_path: str | Path
    ) -> bool:
        """
        Extract the last frame from a video file and save it as an image.
        """
        if not MOVIEPY_AVAILABLE:
            print("MoviePy not available, cannot extract last frame.")
            return False

        try:
            video_path = str(video_path)
            output_image_path = str(output_image_path)

            with VideoFileClip(video_path) as clip:
                # Extract the last frame (minus a small buffer to ensure valid frame)
                duration = clip.duration
                last_frame_time = max(0, duration - 0.1)
                clip.save_frame(output_image_path, t=last_frame_time)

            print(f"Last frame extracted to: {output_image_path}")
            return True
        except Exception as e:
            print(f"Failed to extract last frame: {e}")
            return False

    @staticmethod
    def stitch_videos(video_files: List[str], output_path: Union[str, Path]):
        output_path = Path(output_path)
        if not MOVIEPY_AVAILABLE:
            print("Skipping stitching: moviepy not available.")
            return

        print("Stitching videos...")
        clips = []
        resized_clips = []
        final_clip = None

        try:
            # Load all clips
            clips = [VideoFileClip(f) for f in video_files]
            if not clips:
                return

            # Determine target resolution from the first clip (or default to 1280x720)
            target_w, target_h = clips[0].size
            # Normalize all clips to the target resolution to avoid stitching errors
            for clip in clips:
                if clip.size != (target_w, target_h):
                    print(
                        f"Resizing clip {clip.filename} from {clip.size} to {(target_w, target_h)}"
                    )
                    # Use method='compose' for high quality resizing
                    # Check for resized method (MoviePy v2) vs resize (MoviePy v1)
                    if hasattr(clip, "resized"):
                        resized_clips.append(
                            clip.resized(new_size=(target_w, target_h))
                        )
                    else:
                        resized_clips.append(clip.resize(newsize=(target_w, target_h)))
                else:
                    resized_clips.append(clip)

            # Use method="compose" to handle different formats/resolutions safer
            # Set fps explicitly to avoid mismatch issues
            target_fps = clips[0].fps if clips[0].fps else 24

            final_clip = concatenate_videoclips(resized_clips, method="compose")

            output_path.parent.mkdir(parents=True, exist_ok=True)

            final_clip.write_videofile(
                str(output_path),
                fps=target_fps,
                codec="libx264",
                audio_codec="aac",
                logger=None,
                # audio_bitrate="192k",
                # preset="medium"
            )
            print(f"Full episode video saved: {output_path}")

        except Exception as e:
            print(f"Error during stitching: {e}")
            raise

        finally:
            # Proper resource cleanup
            if final_clip:
                try:
                    final_clip.close()
                except Exception:
                    pass

            # Close resized clips unique from source clips
            for clip in resized_clips:
                if clip not in clips:
                    try:
                        clip.close()
                    except Exception:
                        pass

            # Close original source clips
            for clip in clips:
                try:
                    clip.close()
                except Exception:
                    pass
