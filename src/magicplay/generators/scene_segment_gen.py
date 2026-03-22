"""
Scene Segment Generator Module

Generates multi-frame video segments for Phase 3 of the optimization pipeline.
Handles longer scenes by splitting them into segments and stitching them together.
"""

from pathlib import Path
from typing import List, Optional

from loguru import logger

from magicplay.analyzer.timeline_analyzer import (
    TimelineAnalyzer,
)
from magicplay.config import get_settings
from magicplay.generators.video_gen import VideoGenerator
from magicplay.utils.media import MediaUtils
from magicplay.utils.paths import DataManager


class SceneSegmentGenerator:
    """
    Scene segment generator for Phase 3 multi-frame optimization.

    For scenes longer than 8 seconds, generates multiple key frames
    and creates video segments between them, then stitches for higher quality.
    """

    # Maximum duration for a single video segment (seconds)
    MAX_SEGMENT_DURATION = 10

    def __init__(
        self,
        story_name: str,
        episode_name: str,
        size: tuple = (1280, 720),
        timeline_analyzer: Optional[TimelineAnalyzer] = None,
    ) -> None:
        """
        Initialize scene segment generator.

        Args:
            story_name: Name of the story
            episode_name: Name of the episode
            size: Output video resolution (width, height)
            timeline_analyzer: Optional TimelineAnalyzer for testing.
                               If not provided, a new instance will be created.
        """
        self.story_name = story_name
        self.episode_name = episode_name
        self.size = size
        self.settings = get_settings()

        # Ensure output directory exists
        self.output_dir = DataManager.get_scene_segments_path(story_name, episode_name)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize video generator
        self.video_gen = VideoGenerator()

        # Initialize timeline analyzer (injectable for testing)
        self._timeline_analyzer = timeline_analyzer or TimelineAnalyzer()

        logger.info(f"SceneSegmentGenerator initialized for {story_name}/{episode_name}")

    def generate_scene_segments(
        self,
        scene_name: str,
        scene_script: str,
        base_visual_prompt: str,
        segment_duration: int,
        use_multi_frame: bool = True,
    ) -> List[Path]:
        """
        Generate video segments for a scene.

        For longer scenes, splits into multiple segments with key frames.

        Args:
            scene_name: Name of the scene
            scene_script: Script content for context
            base_visual_prompt: Base visual prompt for video generation
            segment_duration: Total duration of the scene in seconds
            use_multi_frame: Whether to use multi-frame generation

        Returns:
            List of paths to generated video segments
        """
        segments: List[Path] = []

        if not use_multi_frame or segment_duration <= self.MAX_SEGMENT_DURATION:
            # Single segment generation
            segment = self._generate_single_segment(
                scene_name=scene_name,
                visual_prompt=base_visual_prompt,
                duration=segment_duration,
                segment_index=0,
            )
            if segment:
                segments.append(segment)
            return segments

        # Multi-frame generation: split into multiple segments
        num_segments = (segment_duration + self.MAX_SEGMENT_DURATION - 1) // self.MAX_SEGMENT_DURATION
        actual_segment_duration = segment_duration // num_segments

        logger.info(f"Generating {num_segments} segments for scene {scene_name} ({actual_segment_duration}s each)")

        for i in range(num_segments):
            # Create segment-specific prompt
            segment_prompt = self._create_segment_prompt(
                base_prompt=base_visual_prompt,
                segment_index=i,
                total_segments=num_segments,
            )

            segment = self._generate_single_segment(
                scene_name=scene_name,
                visual_prompt=segment_prompt,
                duration=actual_segment_duration,
                segment_index=i,
            )

            if segment:
                segments.append(segment)
            else:
                logger.warning(f"Failed to generate segment {i} for scene {scene_name}")

        return segments

    def generate_with_timeline(
        self,
        scene_name: str,
        scene_script: str,
        segment_duration: int,
        use_multi_frame: bool = True,
    ) -> List[Path]:
        """
        Generate video segments using TimelineAnalyzer for precise per-segment prompts.

        This method uses TimelineAnalyzer to break down the scene script into precise
        time-indexed segments, each with its own visual prompt, rather than using
        the simple "Part N of M" approach.

        Args:
            scene_name: Name of the scene
            scene_script: Script content for timeline analysis
            segment_duration: Total duration of the scene in seconds
            use_multi_frame: Whether to use multi-frame generation

        Returns:
            List of paths to generated video segments
        """
        segments: List[Path] = []

        # Use TimelineAnalyzer to get precise segment prompts
        timeline_result = self._timeline_analyzer.analyze(scene_script=scene_script, duration=segment_duration)

        # Fallback to old behavior if timeline analysis returns empty segments
        if not timeline_result.segments:
            logger.info(
                f"Timeline analysis returned no segments for {scene_name}, falling back to generate_scene_segments"
            )
            return self.generate_scene_segments(
                scene_name=scene_name,
                scene_script=scene_script,
                base_visual_prompt=scene_script,
                segment_duration=segment_duration,
                use_multi_frame=use_multi_frame,
            )

        # Generate each segment using its precise visual prompt from timeline
        for idx, seg in enumerate(timeline_result.segments):
            # Log segment info
            logger.info(f"{seg.start_second}-{seg.end_second}s: {seg.description}")

            segment = self._generate_single_segment(
                scene_name=scene_name,
                visual_prompt=seg.visual_prompt,
                duration=seg.end_second - seg.start_second,
                segment_index=idx,
            )

            if segment:
                segments.append(segment)
            else:
                logger.warning(f"Failed to generate segment {idx} for scene {scene_name}")

        return segments

    def _generate_single_segment(
        self,
        scene_name: str,
        visual_prompt: str,
        duration: int,
        segment_index: int,
    ) -> Optional[Path]:
        """
        Generate a single video segment.

        Args:
            scene_name: Name of the scene
            visual_prompt: Visual prompt for the segment
            duration: Duration in seconds
            segment_index: Index of this segment

        Returns:
            Path to generated video segment, or None if failed
        """
        # Output path for this segment
        output_path = self.output_dir / f"{scene_name}_segment_{segment_index}.mp4"

        try:
            result = self.video_gen.generate_video(
                visual_prompt=visual_prompt,
                output_path=output_path,
                duration=duration,
            )

            if result and result.exists():
                logger.info(f"Generated segment {segment_index}: {result}")
                return result
            else:
                logger.error(f"Failed to generate segment {segment_index}")
                return None

        except Exception as e:
            logger.error(f"Error generating segment {segment_index}: {e}")
            return None

    def stitch_segments(
        self,
        scene_name: str,
        segments: List[Path],
    ) -> Optional[Path]:
        """
        Stitch video segments together into a single video.

        Args:
            scene_name: Name of the scene
            segments: List of paths to video segments

        Returns:
            Path to stitched video, or None if failed
        """
        if not segments:
            logger.error("No segments provided for stitching")
            return None

        if len(segments) == 1:
            # Only one segment, no stitching needed
            return segments[0]

        # Output path for stitched video
        output_path = self.output_dir / f"{scene_name}_stitched.mp4"

        try:
            if MediaUtils.stitch_videos(segments, output_path):
                logger.info(f"Stitched video saved: {output_path}")
                return output_path
            else:
                logger.error("Failed to stitch video segments")
                return None

        except Exception as e:
            logger.error(f"Error stitching segments: {e}")
            return None

    def _create_segment_prompt(
        self,
        base_prompt: str,
        segment_index: int,
        total_segments: int,
    ) -> str:
        """
        Create a prompt for a specific segment.

        Args:
            base_prompt: Base visual prompt
            segment_index: Index of the segment
            total_segments: Total number of segments

        Returns:
            Segment-specific prompt
        """
        # Add segment-specific guidance
        segment_guidance = f"Part {segment_index + 1} of {total_segments}. "
        return segment_guidance + base_prompt
