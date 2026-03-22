"""
Storyboard Generator for Professional Workflow Phase 3.

Generates detailed storyboards with first-frame prompts and motion prompts
for each frame, leveraging TimelineAnalyzer for segmentation.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from magicplay.analyzer.timeline_analyzer import TimelineAnalyzer, TimelineSegment
from magicplay.schema.professional_workflow import (
    CharacterReference,
    SceneReference,
    Storyboard,
    StoryboardFrame,
)


class StoryboardGenerator:
    """
    Generates detailed storyboards with first-frame and motion prompts.

    Phase 3 of the professional workflow takes scene scripts and references
    to create detailed storyboards for video generation.
    """

    def __init__(self, timeline_analyzer: Optional[TimelineAnalyzer] = None):
        """
        Initialize storyboard generator.

        Args:
            timeline_analyzer: Optional TimelineAnalyzer for segmentation.
                              If not provided, creates a default one.
        """
        self._timeline_analyzer = timeline_analyzer or TimelineAnalyzer()

    def generate_storyboard(
        self,
        scene_name: str,
        scene_script: str,
        scene_reference_path: Path,
        character_images: Dict[str, CharacterReference],
        duration: Optional[int] = None,
    ) -> Storyboard:
        """
        Generate a complete storyboard for a scene.

        Args:
            scene_name: Name of the scene
            scene_script: Script content for the scene
            scene_reference_path: Path to 16:9 scene reference image
            character_images: Dict of character name -> CharacterReference
            duration: Optional total duration (auto-calculated if not provided)

        Returns:
            Storyboard object with frames, prompts, and references
        """
        logger.info(f"Generating storyboard for scene: {scene_name}")

        # Analyze timeline to get segments
        if duration is None:
            # Estimate duration from script length
            duration = max(10, min(30, len(scene_script) // 50))

        timeline_result = self._timeline_analyzer.analyze(scene_script, duration)
        segments = timeline_result.segments

        if not segments:
            logger.warning(f"No segments generated for scene: {scene_name}")
            # Create a single segment as fallback
            segments = [
                TimelineSegment(
                    start_second=0,
                    end_second=duration,
                    visual_prompt=scene_script[:200],
                    description="Default segment",
                )
            ]

        # Build storyboard frames from segments
        frames = []
        for i, segment in enumerate(segments):
            # Generate first frame prompt if not provided
            first_frame_prompt = segment.first_frame_prompt or self._generate_first_frame_prompt(
                segment=segment,
                scene_reference_path=scene_reference_path,
                character_images=character_images,
            )

            # Generate motion prompt if not provided
            motion_prompt = segment.motion_prompt or self._generate_motion_prompt(segment)

            frame = StoryboardFrame(
                frame_index=i,
                start_second=segment.start_second,
                end_second=segment.end_second,
                first_frame_prompt=first_frame_prompt,
                motion_prompt=motion_prompt,
                reference_image_path=scene_reference_path,
                characters=self._get_characters_in_segment(segment, character_images),
            )
            frames.append(frame)

        # Extract dialogue lines if present
        dialogue_lines = self._extract_dialogue_lines(scene_script)

        return Storyboard(
            scene_name=scene_name,
            scene_reference_path=scene_reference_path,
            frames=frames,
            total_duration=frames[-1].end_second if frames else duration,
            dialogue_lines=dialogue_lines,
        )

    def _generate_first_frame_prompt(
        self,
        segment: TimelineSegment,
        scene_reference_path: Path,
        character_images: Dict[str, CharacterReference],
    ) -> str:
        """
        Generate first frame prompt for I2I generation.

        Args:
            segment: Timeline segment data
            scene_reference_path: Path to scene reference image
            character_images: Available character reference images

        Returns:
            First frame prompt string
        """
        prompt_parts = []

        # Add scene reference context
        prompt_parts.append(f"Scene reference: {segment.visual_prompt}")

        # Add characters in this segment
        segment_chars = self._get_characters_in_segment(segment, character_images)
        if segment_chars:
            char_names = [c for c in segment_chars]
            prompt_parts.append(f"Characters: {', '.join(char_names)}")

        # Add composition guidance
        prompt_parts.append(
            "medium shot, cinematic composition, anime style, "
            "high quality, detailed, sharp focus"
        )

        return " | ".join(prompt_parts)

    def _generate_motion_prompt(self, segment: TimelineSegment) -> str:
        """
        Generate motion prompt for video generation.

        Args:
            segment: Timeline segment data

        Returns:
            Motion prompt string
        """
        # Use description as base, make it action-oriented
        motion = segment.description

        # Add motion keywords if not present
        motion_keywords = ["moving", "action", "motion"]
        has_motion = any(kw in motion.lower() for kw in motion_keywords)

        if not has_motion:
            motion = f"{motion}, gentle movement"

        # Add camera guidance
        motion = f"{motion}, camera stable"

        return motion

    def _get_characters_in_segment(
        self,
        segment: TimelineSegment,
        character_images: Dict[str, CharacterReference],
    ) -> List[str]:
        """Get character names relevant to this segment."""
        # For now, return all characters - could be enhanced to filter by segment
        return list(character_images.keys())

    def _extract_dialogue_lines(self, scene_script: str) -> List[Dict[str, str]]:
        """
        Extract dialogue lines from script.

        Args:
            scene_script: Script content

        Returns:
            List of dicts with 'character' and 'text' keys
        """
        import re

        dialogue_lines = []
        lines = scene_script.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()

            # Look for character names in bold
            match = re.match(r"^\*\*([^*]+)\*\*$", line)
            if match and len(match.group(1)) > 1:
                char_name = match.group(1).strip()
                # Skip if it's a heading
                if char_name.upper() in {"SCENE", "INT", "EXT", "ACTION", "DIALOGUE"}:
                    continue

                # Check next line for dialogue
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith("#"):
                        dialogue_lines.append(
                            {"character": char_name, "text": next_line[:200]}
                        )

        return dialogue_lines

    def save_storyboard(
        self,
        storyboard: Storyboard,
        output_dir: Path,
    ) -> Path:
        """
        Save storyboard to JSON file.

        Args:
            storyboard: Storyboard to save
            output_dir: Output directory

        Returns:
            Path to saved JSON file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._sanitize_filename(storyboard.scene_name)
        output_path = output_dir / f"{safe_name}.json"

        # Convert to JSON-friendly format
        data = {
            "scene_name": storyboard.scene_name,
            "scene_reference_path": str(storyboard.scene_reference_path),
            "total_duration": storyboard.total_duration,
            "frames": [
                {
                    "frame_index": f.frame_index,
                    "start_second": f.start_second,
                    "end_second": f.end_second,
                    "first_frame_prompt": f.first_frame_prompt,
                    "motion_prompt": f.motion_prompt,
                    "first_frame_path": str(f.first_frame_path) if f.first_frame_path else None,
                    "video_segment_path": str(f.video_segment_path) if f.video_segment_path else None,
                    "characters": f.characters,
                }
                for f in storyboard.frames
            ],
            "dialogue_lines": storyboard.dialogue_lines,
        }

        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(f"Storyboard saved to: {output_path}")
        return output_path

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize scene name for use as filename."""
        import re
        safe = re.sub(r"[^\w\s\-]", "_", name)
        safe = re.sub(r"[\s]+", "_", safe)
        return safe[:100]

    @staticmethod
    def load_storyboard(storyboard_path: Path) -> Optional[Storyboard]:
        """
        Load storyboard from JSON file.

        Args:
            storyboard_path: Path to storyboard JSON file

        Returns:
            Storyboard object or None on failure
        """
        try:
            data = json.loads(storyboard_path.read_text(encoding="utf-8"))

            frames = []
            for f_data in data.get("frames", []):
                frame = StoryboardFrame(
                    frame_index=f_data["frame_index"],
                    start_second=f_data["start_second"],
                    end_second=f_data["end_second"],
                    first_frame_prompt=f_data.get("first_frame_prompt", ""),
                    motion_prompt=f_data.get("motion_prompt", ""),
                    first_frame_path=Path(f_data["first_frame_path"]) if f_data.get("first_frame_path") else None,
                    video_segment_path=Path(f_data["video_segment_path"]) if f_data.get("video_segment_path") else None,
                    characters=f_data.get("characters", []),
                )
                frames.append(frame)

            return Storyboard(
                scene_name=data["scene_name"],
                scene_reference_path=Path(data["scene_reference_path"]),
                frames=frames,
                total_duration=data.get("total_duration", 0),
                dialogue_lines=data.get("dialogue_lines", []),
            )

        except Exception as e:
            logger.error(f"Failed to load storyboard from {storyboard_path}: {e}")
            return None
