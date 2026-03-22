"""
TimelineAnalyzer - Analyzes scene scripts to generate time-indexed video segments.

Uses LLM to parse scene scripts into precise time-indexed segments with
individual visual prompts for each segment.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from loguru import logger

from magicplay.services.llm import LLMService


@dataclass
class TimelineSegment:
    """A time-indexed segment of a video timeline."""

    MIN_SEGMENT_DURATION = 3

    start_second: int
    end_second: int
    visual_prompt: str
    description: str
    first_frame_prompt: str = ""  # NEW: Prompt for I2I first frame generation
    motion_prompt: str = ""  # NEW: Prompt for video generation motion

    def __post_init__(self):
        """Validate segment data."""
        if self.end_second <= self.start_second:
            raise ValueError(
                f"end_second ({self.end_second}) must be greater than "
                f"start_second ({self.start_second})"
            )
        if self.end_second - self.start_second < self.MIN_SEGMENT_DURATION:
            raise ValueError(
                f"Segment duration ({self.end_second - self.start_second}s) "
                f"must be at least {self.MIN_SEGMENT_DURATION} seconds"
            )

    @property
    def duration(self) -> int:
        """Get segment duration in seconds."""
        return self.end_second - self.start_second


@dataclass
class TimelineResult:
    """Result of timeline analysis containing all segments."""

    segments: List[TimelineSegment]
    total_duration: int
    reasoning: str


class TimelineAnalyzer:
    """
    Analyzes scene scripts using LLM to generate time-indexed video segments.

    This analyzer takes a scene script and desired duration, then uses an LLM
    to break it down into precise time-indexed segments, each with its own
    visual prompt for video generation.

    Attributes:
        llm_service: LLM service instance for generating timeline analysis
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize TimelineAnalyzer.

        Args:
            llm_service: Optional LLM service for testing. If not provided,
                        a new LLMService will be created.
        """
        if llm_service is not None:
            self._llm_service = llm_service
        else:
            self._llm_service = LLMService()

    def analyze(self, scene_script: str, duration: int) -> TimelineResult:
        """
        Analyze scene script and generate time-indexed segments.

        Args:
            scene_script: The scene script text to analyze
            duration: Total duration of the video in seconds

        Returns:
            TimelineResult containing list of segments and metadata
        """
        if not scene_script:
            logger.warning("Empty scene script provided, returning empty result")
            return TimelineResult(
                segments=[],
                total_duration=duration,
                reasoning="Empty scene script provided",
            )

        # Read prompt template
        prompt_template = self._load_prompt_template()

        # Construct user prompt with scene script and duration
        user_prompt = prompt_template.format(
            scene_script=scene_script, duration=duration
        )

        # System prompt for the LLM
        system_prompt = (
            "你是一个专业的视频分镜专家，擅长将场景脚本分割成精确的时间片段。"
        )

        # Call LLM
        try:
            response = self._llm_service.generate_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # Lower temperature for structured output
                max_tokens=2000,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return TimelineResult(
                segments=[],
                total_duration=duration,
                reasoning=f"LLM call failed: {str(e)}",
            )

        # Parse JSON response
        return self._parse_response(response, duration)

    def _load_prompt_template(self) -> str:
        """Load the prompt template from file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "timeline_analyze.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

        # Fallback to default template
        return """你是一个专业的视频分镜专家。根据场景脚本和总时长，
将视频内容切分成多个时间片段，每个片段有独立的视觉描述。

要求：
- 最小分镜时长：3秒
- 每个片段的 visual_prompt 必须精准描述该时间段的画面内容
- 考虑镜头语言：推、拉、摇、移、跟等
- 考虑动作连贯性：前一镜头的结束动作与后一镜头的开始动作应衔接自然
- 输出有效的 JSON 格式

场景脚本：{scene_script}

总时长：{duration} 秒

请以 JSON 格式返回分镜结果，格式如下：
{{
    "segments": [
        {{
            "start_second": 0,
            "end_second": 5,
            "visual_prompt": "该时间段的视觉描述prompt",
            "description": "该时间段的详细描述"
        }},
        ...
    ],
    "reasoning": "分镜推理过程说明"
}}"""

    def _parse_response(self, response: str, duration: int) -> TimelineResult:
        """
        Parse LLM JSON response into TimelineResult.

        Args:
            response: JSON response string from LLM
            duration: Total duration for validation

        Returns:
            TimelineResult with parsed segments
        """
        try:
            # Try to extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            segments = []
            for seg_data in data.get("segments", []):
                try:
                    segment = TimelineSegment(
                        start_second=int(seg_data["start_second"]),
                        end_second=int(seg_data["end_second"]),
                        visual_prompt=str(seg_data["visual_prompt"]),
                        description=str(seg_data["description"]),
                        first_frame_prompt=str(seg_data.get("first_frame_prompt", "")),
                        motion_prompt=str(seg_data.get("motion_prompt", "")),
                    )
                    segments.append(segment)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid segment data: {seg_data}, error: {e}")
                    continue

            return TimelineResult(
                segments=segments,
                total_duration=duration,
                reasoning=data.get("reasoning", ""),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return TimelineResult(
                segments=[],
                total_duration=duration,
                reasoning=f"JSON parse error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return TimelineResult(
                segments=[], total_duration=duration, reasoning=f"Parse error: {str(e)}"
            )

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON string from LLM response text.

        Handles cases where the LLM wraps JSON in markdown code blocks
        or adds extra text before/after the JSON.

        Args:
            text: Raw response text from LLM

        Returns:
            Cleaned JSON string
        """
        # Try direct parsing first
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Look for JSON in code blocks
        # Match ```json ... ``` blocks
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to find JSON object starting with { and ending with }
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        # If nothing works, return original text and let json.loads fail
        return text
