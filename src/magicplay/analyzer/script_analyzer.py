import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SceneType(Enum):
    DIALOGUE = "dialogue"
    ACTION = "action"
    TRANSITION = "transition"
    MIXED = "mixed"


@dataclass
class AnalysisResult:
    """Result of script analysis."""

    total_words: int
    dialogue_lines: int
    action_density: float  # 0-1, proportion of action descriptions
    scene_type: SceneType
    estimated_duration: int  # in seconds
    complexity_score: float  # 0-1
    character_count: int
    location_changes: int
    metadata: Dict[str, Any]


class ScriptAnalyzer:
    """
    Analyzes script content to determine appropriate video duration and other parameters.
    """

    def __init__(self, min_duration: int = 5, max_duration: int = 30):
        """
        Initialize analyzer with duration limits.

        Args:
            min_duration: Minimum video duration in seconds (API/model limit)
            max_duration: Maximum video duration in seconds (API/model limit)
        """
        self.min_duration = min_duration
        self.max_duration = max_duration

    def analyze(self, script_content: str) -> AnalysisResult:
        """
        Analyze script content and determine optimal video duration.

        Args:
            script_content: Full script text in markdown format

        Returns:
            AnalysisResult with estimated duration and other metrics
        """
        if not script_content:
            return self._default_result()

        # Basic text analysis
        total_words = self._count_words(script_content)
        dialogue_lines = self._count_dialogue_lines(script_content)
        action_density = self._calculate_action_density(script_content)
        character_count = self._count_characters(script_content)
        location_changes = self._count_location_changes(script_content)

        # Determine scene type
        scene_type = self._classify_scene_type(
            dialogue_lines, action_density, total_words
        )

        # Calculate complexity score (0-1)
        complexity_score = self._calculate_complexity_score(
            total_words,
            dialogue_lines,
            action_density,
            character_count,
            location_changes,
        )

        # Estimate duration based on complexity and scene type
        estimated_duration = self._estimate_duration(
            scene_type, complexity_score, total_words
        )

        # Ensure duration within limits
        estimated_duration = max(
            self.min_duration, min(self.max_duration, estimated_duration)
        )

        return AnalysisResult(
            total_words=total_words,
            dialogue_lines=dialogue_lines,
            action_density=action_density,
            scene_type=scene_type,
            estimated_duration=estimated_duration,
            complexity_score=complexity_score,
            character_count=character_count,
            location_changes=location_changes,
            metadata={
                "word_count": total_words,
                "dialogue_ratio": dialogue_lines
                / max(1, total_words / 10),  # rough ratio
                "has_action": action_density > 0.3,
            },
        )

    def _count_words(self, text: str) -> int:
        """Count words in script, handling both Chinese and English."""
        # Remove markdown formatting and stage directions
        clean_text = re.sub(r"\*\*.*?\*\*", "", text)  # Remove bold
        clean_text = re.sub(r"#+.*?\n", "", clean_text)  # Remove headers
        clean_text = re.sub(r"\[.*?\]", "", clean_text)  # Remove stage directions
        clean_text = re.sub(r"\(.*?\)", "", clean_text)  # Remove parentheticals

        # Split into words/characters
        # For Chinese: each character counts as a word
        # For English: split by whitespace and punctuation
        words = []
        current_word = ""

        for char in clean_text:
            if re.match(r"[\u4e00-\u9fff]", char):  # Chinese character
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append(char)  # Each Chinese character counts as a word
            elif re.match(r"[A-Za-z0-9]", char):  # English alphanumeric
                current_word += char
            else:  # Separator
                if current_word:
                    words.append(current_word)
                    current_word = ""

        if current_word:
            words.append(current_word)

        return len(words)

    def _count_dialogue_lines(self, text: str) -> int:
        """Count lines of dialogue (lines ending with parenthetical or plain dialogue)."""
        # Simple heuristic: lines that are all caps (character names) followed by dialogue
        lines = text.split("\n")
        dialogue_count = 0
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Check for character name (often in caps or has specific pattern)
            if (line.isupper() or re.match(r"^[A-Z][A-Z\s]+$", line)) and len(line) > 2:
                # Next line might be dialogue or parenthetical
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith("(") or (
                        len(next_line) > 0 and not next_line.startswith("#")
                    ):
                        dialogue_count += 1
                        i += 1  # Skip dialogue line
            i += 1
        return dialogue_count

    def _calculate_action_density(self, text: str) -> float:
        """
        Calculate proportion of action descriptions.
        Simple heuristic: look for ACTION headers and descriptive text.
        """
        lines = text.split("\n")
        action_lines = 0
        total_lines = len(lines)

        if total_lines == 0:
            return 0.0

        in_action_section = False
        for line in lines:
            line_lower = line.lower().strip()
            if "action" in line_lower and "**" in line:
                in_action_section = True
            elif line_lower.startswith("###") or line_lower.startswith("##"):
                in_action_section = False
            elif in_action_section and line.strip():
                action_lines += 1
            elif not in_action_section and "**" in line and "action" not in line_lower:
                # Might be action description outside formal section
                if len(line.split()) > 5:  # Descriptive line
                    action_lines += 1

        return min(1.0, action_lines / max(1, total_lines))

    def _count_characters(self, text: str) -> int:
        """Count distinct characters mentioned in script."""
        # Look for character names in bold or all caps
        character_patterns = [
            r"\*\*([A-Z][A-Za-z\s]+)\*\*",  # **CHARACTER NAME**
            r"^([A-Z][A-Z\s]+)$",  # All caps line
        ]

        characters = set()
        for pattern in character_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                name = match.strip()
                if (
                    len(name) > 2
                    and not name.startswith("SCENE")
                    and not name.startswith("ACTION")
                ):
                    characters.add(name)

        return len(characters)

    def _count_location_changes(self, text: str) -> int:
        """Count location changes based on scene headers."""
        # Look for scene headers like "INT. LOCATION - TIME"
        # Match lines that start with INT., EXT., or INT/EXT. followed by location and time
        scene_pattern = r"^(?:INT\.|EXT\.|INT/EXT\.)\s+[^-]+-\s*[^-]+$"
        matches = re.findall(scene_pattern, text, re.MULTILINE | re.IGNORECASE)
        return len(matches)

    def _classify_scene_type(
        self, dialogue_lines: int, action_density: float, total_words: int
    ) -> SceneType:
        """Classify scene based on dialogue vs action balance."""
        if total_words < 500:  # Increased threshold for Chinese content
            return SceneType.TRANSITION

        # Adjusted normalization for Chinese scripts
        dialogue_ratio = dialogue_lines / max(1, total_words / 15)

        if dialogue_ratio > 0.4 and action_density < 0.3:
            return SceneType.DIALOGUE
        elif action_density > 0.4 and dialogue_ratio < 0.4:
            return SceneType.ACTION
        elif dialogue_ratio < 0.15 and action_density < 0.2:
            return SceneType.TRANSITION
        else:
            return SceneType.MIXED

    def _calculate_complexity_score(
        self,
        total_words: int,
        dialogue_lines: int,
        action_density: float,
        character_count: int,
        location_changes: int,
    ) -> float:
        """Calculate complexity score (0-1)."""
        # Normalize each factor
        word_score = min(1.0, total_words / 2000)  # 2000 words = max score
        dialogue_score = min(1.0, dialogue_lines / 50)  # 50 dialogue lines = max
        action_score = action_density  # Already 0-1
        character_score = min(1.0, character_count / 10)  # 10 characters = max
        location_score = min(1.0, location_changes / 5)  # 5 locations = max

        # Weighted average (adjust weights as needed)
        weights = {
            "words": 0.3,
            "dialogue": 0.2,
            "action": 0.25,
            "characters": 0.15,
            "locations": 0.1,
        }

        score = (
            word_score * weights["words"]
            + dialogue_score * weights["dialogue"]
            + action_score * weights["action"]
            + character_score * weights["characters"]
            + location_score * weights["locations"]
        )

        return min(1.0, score)

    def _estimate_duration(
        self, scene_type: SceneType, complexity_score: float, total_words: int
    ) -> int:
        """
        Estimate optimal video duration based on scene type and complexity.

        Base durations (adjusted for 5-30 second range):
        - Transition: 3-8 seconds
        - Dialogue: 8-18 seconds
        - Action: 12-30 seconds
        - Mixed: 10-25 seconds

        Complexity adjusts within these ranges.
        """
        # Adjusted base ranges by scene type for 5-30 second range
        ranges = {
            SceneType.TRANSITION: (3, 8),
            SceneType.DIALOGUE: (8, 18),
            SceneType.ACTION: (12, 30),
            SceneType.MIXED: (10, 25),
        }

        min_dur, max_dur = ranges.get(scene_type, (8, 20))

        # Adjust by complexity
        duration = min_dur + (max_dur - min_dur) * complexity_score

        # Adjust by word count
        # For Chinese scripts, 500 characters ≈ 1 minute of dialogue
        # Video typically shows 150-200 words per 10 seconds
        word_factor = max(0.7, min(1.5, total_words / 600))
        duration *= word_factor

        # Ensure minimum duration of at least min_dur * 0.7
        duration = max(min_dur * 0.7, duration)

        return int(round(duration))

    def _default_result(self) -> AnalysisResult:
        """Return default result for empty script."""
        return AnalysisResult(
            total_words=0,
            dialogue_lines=0,
            action_density=0.0,
            scene_type=SceneType.TRANSITION,
            estimated_duration=self.min_duration,
            complexity_score=0.0,
            character_count=0,
            location_changes=0,
            metadata={"default": True},
        )

    def analyze_file(self, script_path: str) -> Optional[AnalysisResult]:
        """Analyze script from file."""
        try:
            from pathlib import Path

            path_obj = Path(script_path)
            if path_obj.exists():
                content = path_obj.read_text(encoding="utf-8")
                return self.analyze(content)
        except Exception as e:
            print(f"Error analyzing script file {script_path}: {e}")
        return None
