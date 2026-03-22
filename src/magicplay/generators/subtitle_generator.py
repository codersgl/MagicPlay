"""
Subtitle Generator for Professional Workflow Phase 6.

Generates SRT subtitles from script content and timing data.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from magicplay.schema.professional_workflow import SubtitleCue


class SubtitleGenerator:
    """
    Generates SRT subtitles from script content and timing data.

    Phase 6 takes script dialogue and timing information to create
    proper SRT subtitle files for video burning or soft-subtitle display.
    """

    def __init__(self):
        """Initialize subtitle generator."""
        pass

    def generate_subtitles(
        self,
        dialogue_lines: List[Dict[str, str]],
        timing_data: List[Dict[str, int]],
        output_path: Path,
    ) -> Path:
        """
        Generate SRT subtitle file from dialogue and timing.

        Args:
            dialogue_lines: List of dicts with 'character' and 'text' keys
            timing_data: List of dicts with 'start_second' and 'end_second' keys
                          (should align with dialogue_lines)
            output_path: Path to save the SRT file

        Returns:
            Path to generated SRT file
        """
        if not dialogue_lines:
            logger.warning("No dialogue lines provided for subtitles")
            return self._create_empty_subtitle(output_path)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cues = []
        for i, (dialogue, timing) in enumerate(zip(dialogue_lines, timing_data)):
            cue = SubtitleCue(
                index=i + 1,
                start_time=float(timing.get("start_second", 0)),
                end_time=float(
                    timing.get("end_second", timing.get("start_second", 0) + 3)
                ),
                text=dialogue.get("text", ""),
                character=dialogue.get("character", ""),
            )
            cues.append(cue)

        # Write SRT file
        srt_content = self._build_srt_content(cues)
        output_path.write_text(srt_content, encoding="utf-8")

        logger.info(f"Subtitles generated: {output_path} ({len(cues)} cues)")
        return output_path

    def generate_subtitles_from_script(
        self,
        script_content: str,
        duration: int,
        output_path: Path,
    ) -> Path:
        """
        Generate subtitles directly from script content.

        Automatically extracts dialogue and estimates timing based on
        average speaking rate.

        Args:
            script_content: Script content with dialogue
            duration: Total video duration in seconds
            output_path: Path to save the SRT file

        Returns:
            Path to generated SRT file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract dialogue from script
        dialogue_lines = self._extract_dialogue(script_content)

        if not dialogue_lines:
            logger.warning("No dialogue found in script")
            return self._create_empty_subtitle(output_path)

        # Estimate timing
        timing_data = self._estimate_timing(dialogue_lines, duration)

        return self.generate_subtitles(dialogue_lines, timing_data, output_path)

    def _extract_dialogue(self, script_content: str) -> List[Dict[str, str]]:
        """
        Extract dialogue lines from script content.

        Args:
            script_content: Script content

        Returns:
            List of dicts with 'character' and 'text' keys
        """
        dialogue_lines = []
        lines = script_content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for character names in bold
            match = re.match(r"^\*\*([^*]+)\*\*$", line)
            if match:
                char_name = match.group(1).strip()
                # Skip if it's a heading
                skip_words = {"SCENE", "INT", "EXT", "ACTION", "DIALOGUE", "SUMMARY"}
                if char_name.upper() not in skip_words and len(char_name) > 1:
                    # Check next line for dialogue
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not next_line.startswith("#"):
                            # Clean dialogue text
                            clean_text = self._clean_dialogue_text(next_line)
                            if clean_text:
                                dialogue_lines.append(
                                    {"character": char_name, "text": clean_text}
                                )
            i += 1

        return dialogue_lines

    def _clean_dialogue_text(self, text: str) -> str:
        """Clean dialogue text for subtitles."""
        # Remove stage directions in brackets
        text = re.sub(r"\[([^\]]+)\]", "", text)
        # Remove parentheticals
        text = re.sub(r"\(([^)]+)\)", "", text)
        # Remove markdown formatting
        text = re.sub(r"\*+", "", text)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _estimate_timing(
        self,
        dialogue_lines: List[Dict[str, str]],
        total_duration: int,
    ) -> List[Dict[str, int]]:
        """
        Estimate timing for dialogue lines based on text length.

        Args:
            dialogue_lines: List of dialogue dicts
            total_duration: Total video duration

        Returns:
            List of timing dicts
        """
        if not dialogue_lines:
            return []

        # Calculate total speaking time (leave room for pauses)
        total_words = sum(len(line["text"].split()) for line in dialogue_lines)
        if total_words == 0:
            total_words = len(dialogue_lines) * 5  # Default 5 words per line

        # Average speaking rate: ~2.5 words per second
        speaking_time = total_words / 2.5
        pause_ratio = 0.2  # 20% of time is pauses
        effective_duration = total_duration * (1 - pause_ratio)

        # Scale speaking time to fit
        scale = effective_duration / speaking_time if speaking_time > 0 else 1

        timing_data = []
        current_time = 0

        for line in dialogue_lines:
            word_count = len(line["text"].split())
            # Calculate duration based on word count
            segment_duration = max(2, int(word_count * scale))

            # Add some variance
            import random

            variance = random.randint(-1, 1)
            segment_duration = max(2, segment_duration + variance)

            timing_data.append(
                {
                    "start_second": current_time,
                    "end_second": current_time + segment_duration,
                }
            )
            current_time += segment_duration

        # Adjust to fit within total duration
        if timing_data and current_time > total_duration:
            # Scale down
            scale = total_duration / current_time
            for timing in timing_data:
                timing["start_second"] = int(timing["start_second"] * scale)
                timing["end_second"] = int(timing["end_second"] * scale)

        return timing_data

    def _build_srt_content(self, cues: List[SubtitleCue]) -> str:
        """
        Build SRT file content from subtitle cues.

        Args:
            cues: List of SubtitleCue objects

        Returns:
            SRT-formatted string
        """
        return "\n".join(cue.to_srt_format() for cue in cues)

    def _create_empty_subtitle(self, output_path: Path) -> Path:
        """Create an empty SRT file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create minimal SRT with one empty cue
        content = "1\n00:00:00,000 --> 00:00:05,000\n(No dialogue)\n"
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def merge_subtitle_files(
        self,
        subtitle_files: List[Path],
        output_path: Path,
    ) -> Path:
        """
        Merge multiple SRT files into one.

        Args:
            subtitle_files: List of SRT file paths
            output_path: Path to save merged SRT

        Returns:
            Path to merged SRT file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        all_cues = []
        cue_index = 1
        current_time = 0.0

        for srt_file in subtitle_files:
            if not srt_file.exists():
                continue

            cues = self._parse_srt_file(srt_file)

            for cue in cues:
                # Adjust timing
                duration = cue.end_time - cue.start_time
                cue.index = cue_index
                cue.start_time = current_time
                cue.end_time = current_time + duration

                all_cues.append(cue)
                cue_index += 1
                current_time += duration + 0.5  # Add 0.5s gap between cues

        # Write merged SRT
        content = self._build_srt_content(all_cues)
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Merged {len(subtitle_files)} subtitles into: {output_path}")
        return output_path

    def _parse_srt_file(self, srt_path: Path) -> List[SubtitleCue]:
        """Parse an SRT file into SubtitleCue objects."""
        cues = []
        content = srt_path.read_text(encoding="utf-8")

        # Split into subtitle blocks
        blocks = re.split(r"\n\n+", content)

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 2:
                continue

            # Parse index
            try:
                index = int(lines[0].strip())
            except ValueError:
                continue

            # Parse timing
            timing_match = re.match(
                r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
                lines[1],
            )
            if not timing_match:
                continue

            start = self._parse_srt_timestamp(timing_match.group(1))
            end = self._parse_srt_timestamp(timing_match.group(2))

            # Parse text
            text = "\n".join(lines[2:]) if len(lines) > 2 else ""

            cues.append(
                SubtitleCue(
                    index=index,
                    start_time=start,
                    end_time=end,
                    text=text,
                )
            )

        return cues

    @staticmethod
    def _parse_srt_timestamp(timestamp: str) -> float:
        """Parse SRT timestamp to float seconds."""
        match = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", timestamp)
        if match:
            h, m, s, ms = match.groups()
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        return 0.0
