"""
Video Synthesis Generator for Professional Workflow Phase 6.

Handles final video synthesis: stitch videos, add subtitles, add background music.
"""

from pathlib import Path
from typing import List, Optional

from loguru import logger

from magicplay.schema.professional_workflow import VideoClip
from magicplay.utils.media import MediaUtils


class VideoSynthesisGenerator:
    """
    Final video synthesis for professional workflow.

    Phase 6 takes all video segments, subtitles, and music to produce
    the final complete short drama video.
    """

    def __init__(self):
        """Initialize video synthesis generator."""
        self._media_utils = MediaUtils()

    def synthesize(
        self,
        video_clips: List[VideoClip],
        output_path: Path,
        add_subtitles: bool = True,
        add_music: bool = False,
        subtitle_path: Optional[Path] = None,
        music_path: Optional[Path] = None,
        music_volume: float = 0.3,
    ) -> Path:
        """
        Synthesize final video with all components.

        Args:
            video_clips: List of VideoClip objects with video paths and metadata
            output_path: Path for final output video
            add_subtitles: Whether to burn subtitles into video
            add_music: Whether to add background music
            subtitle_path: Path to SRT subtitle file (required if add_subtitles=True)
            music_path: Path to music file (required if add_music=True)
            music_volume: Background music volume (0.0 to 1.0)

        Returns:
            Path to final synthesized video
        """
        if not video_clips:
            raise ValueError("No video clips provided for synthesis")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting video synthesis: {len(video_clips)} clips")

        # Step 1: Stitch video clips
        video_files = [
            str(clip.video_path) for clip in video_clips if clip.video_path.exists()
        ]
        if not video_files:
            raise ValueError("No valid video files to stitch")

        stitched_path = output_path.with_name(f"{output_path.stem}_raw.mp4")
        self._media_utils.stitch_videos(video_files, stitched_path)

        if not stitched_path.exists():
            raise RuntimeError("Video stitching failed")

        logger.info(f"Video stitched: {stitched_path}")

        # Step 2: Add subtitles if requested
        if add_subtitles and subtitle_path and subtitle_path.exists():
            subtitled_path = output_path.with_name(f"{output_path.stem}_with_subs.mp4")
            self._media_utils.add_subtitles(
                video_path=stitched_path,
                subtitle_path=subtitle_path,
                output_path=subtitled_path,
            )

            if subtitled_path.exists():
                stitched_path = subtitled_path
                logger.info(f"Subtitles added: {subtitled_path}")

        # Step 3: Add background music if requested
        if add_music and music_path and music_path.exists():
            with_music_path = output_path.with_name(f"{output_path.stem}_with_bgm.mp4")
            self._media_utils.add_background_music(
                video_path=stitched_path,
                music_path=music_path,
                output_path=with_music_path,
                volume=music_volume,
            )

            if with_music_path.exists():
                stitched_path = with_music_path
                logger.info(f"Background music added: {with_music_path}")

        # Step 4: Move to final output
        import shutil

        shutil.move(str(stitched_path), str(output_path))

        logger.info(f"Final video synthesized: {output_path}")
        return output_path

    def synthesize_with_storyboard(
        self,
        storyboards: List,  # Storyboard objects
        output_path: Path,
        add_subtitles: bool = True,
        add_music: bool = False,
        music_path: Optional[Path] = None,
        music_volume: float = 0.3,
    ) -> Path:
        """
        Synthesize final video from storyboards.

        Args:
            storyboards: List of Storyboard objects
            output_path: Path for final output video
            add_subtitles: Whether to add subtitles
            add_music: Whether to add background music
            music_path: Path to music file
            music_volume: Background music volume

        Returns:
            Path to final synthesized video
        """
        # Collect all video segments from storyboards
        video_clips = []

        for storyboard in storyboards:
            for frame in storyboard.frames:
                if frame.video_segment_path and frame.video_segment_path.exists():
                    clip = VideoClip(
                        video_path=frame.video_segment_path,
                        start_time=frame.start_second,
                        end_time=frame.end_second,
                        clip_id=f"{storyboard.scene_name}_frame_{frame.frame_index}",
                    )
                    video_clips.append(clip)

        if not video_clips:
            raise ValueError("No video segments found in storyboards")

        # Extract subtitle path if available
        subtitle_path = None
        if add_subtitles:
            # Look for subtitle file in final output directory
            final_dir = output_path.parent
            potential_subtitle = final_dir / "subtitles.srt"
            if potential_subtitle.exists():
                subtitle_path = potential_subtitle

        return self.synthesize(
            video_clips=video_clips,
            output_path=output_path,
            add_subtitles=add_subtitles,
            add_music=add_music,
            subtitle_path=subtitle_path,
            music_path=music_path,
            music_volume=music_volume,
        )

    def create_clip_list_json(
        self,
        video_clips: List[VideoClip],
        output_path: Path,
    ) -> Path:
        """
        Create clip_list.json for video clips.

        Args:
            video_clips: List of VideoClip objects
            output_path: Path to save clip_list.json

        Returns:
            Path to clip_list.json
        """
        import json

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        clips_data = []
        for clip in video_clips:
            clips_data.append(
                {
                    "id": clip.clip_id,
                    "video_path": str(clip.video_path),
                    "start_time": clip.start_time,
                    "end_time": clip.end_time,
                    "duration": clip.duration,
                    "transition": clip.transition,
                    "subtitle_path": (
                        str(clip.subtitle_path) if clip.subtitle_path else None
                    ),
                }
            )

        data = {
            "total_clips": len(clips_data),
            "total_duration": sum(c.duration for c in video_clips),
            "clips": clips_data,
        }

        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(f"Clip list saved: {output_path}")
        return output_path
