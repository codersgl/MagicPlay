from pathlib import Path
from typing import List, Union

import requests
from tqdm import tqdm

try:
    from moviepy import VideoFileClip, concatenate_videoclips

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("Warning: moviepy not installed or import error. Video stitching will be skipped.")


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
    def extract_last_frame(video_path: str | Path, output_image_path: str | Path) -> bool:
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
                    print(f"Resizing clip {clip.filename} from {clip.size} to {(target_w, target_h)}")
                    # Use method='compose' for high quality resizing
                    # Check for resized method (MoviePy v2) vs resize (MoviePy v1)
                    if hasattr(clip, "resized"):
                        resized_clips.append(clip.resized(new_size=(target_w, target_h)))
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

    @staticmethod
    def add_subtitles(
        video_path: Union[str, Path],
        subtitle_path: Union[str, Path],
        output_path: Union[str, Path],
    ) -> bool:
        """
        Add subtitles (SRT) to a video file using ffmpeg.

        Args:
            video_path: Path to input video
            subtitle_path: Path to SRT subtitle file
            output_path: Path for output video with subtitles

        Returns:
            True on success, False on failure
        """
        import subprocess

        video_path = Path(video_path)
        subtitle_path = Path(subtitle_path)
        output_path = Path(output_path)

        if not video_path.exists():
            print(f"Video file not found: {video_path}")
            return False

        if not subtitle_path.exists():
            print(f"Subtitle file not found: {subtitle_path}")
            return False

        try:
            # Use ffmpeg to burn subtitles into video
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i",
                str(video_path),
                "-vf",
                f"subtitles='{subtitle_path}':force_style='FontSize=24,FontName=Arial,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2'",
                "-c:a",
                "copy",  # Copy audio stream
                str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print(f"Subtitles added: {output_path}")
                return True
            else:
                print(f"FFmpeg error: {result.stderr}")
                return False

        except FileNotFoundError:
            print("FFmpeg not found. Please install ffmpeg to add subtitles.")
            return False
        except Exception as e:
            print(f"Failed to add subtitles: {e}")
            return False

    @staticmethod
    def add_background_music(
        video_path: Union[str, Path],
        music_path: Union[str, Path],
        output_path: Union[str, Path],
        volume: float = 0.3,
    ) -> bool:
        """
        Add background music to a video file.

        Args:
            video_path: Path to input video
            music_path: Path to music file
            output_path: Path for output video with music
            volume: Music volume (0.0 to 1.0)

        Returns:
            True on success, False on failure
        """
        import subprocess

        video_path = Path(video_path)
        music_path = Path(music_path)
        output_path = Path(output_path)

        if not video_path.exists():
            print(f"Video file not found: {video_path}")
            return False

        if not music_path.exists():
            print(f"Music file not found: {music_path}")
            return False

        try:
            # Check if video has audio
            has_audio_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                str(video_path),
            ]

            has_audio = (
                subprocess.run(
                    has_audio_cmd,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                == "audio"
            )

            if has_audio:
                # Mix original audio with background music
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_path),
                    "-stream_loop",
                    "-1",  # Loop music
                    "-i",
                    str(music_path),
                    "-filter_complex",
                    f"[1:a]volume={volume}[music];[0:a][music]amix=inputs=2:duration=first[a]",
                    "-map",
                    "0:v",
                    "-map",
                    "[a]",
                    "-c:v",
                    "copy",
                    "-shortest",
                    str(output_path),
                ]
            else:
                # No original audio, just add music
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_path),
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(music_path),
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-c:v",
                    "copy",
                    "-shortest",
                    str(output_path),
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                print(f"Background music added: {output_path}")
                return True
            else:
                print(f"FFmpeg error: {result.stderr}")
                return False

        except FileNotFoundError:
            print("FFmpeg not found. Please install ffmpeg to add background music.")
            return False
        except Exception as e:
            print(f"Failed to add background music: {e}")
            return False
