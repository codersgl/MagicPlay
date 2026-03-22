import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from magicplay.schema.professional_workflow import (
    CharacterInfo,
    CharacterRole,
    SceneInfo,
)
from magicplay.schema.professional_workflow import SceneType as ProfessionalSceneType


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
        scene_type = self._classify_scene_type(dialogue_lines, action_density, total_words)

        # Calculate complexity score (0-1)
        complexity_score = self._calculate_complexity_score(
            total_words,
            dialogue_lines,
            action_density,
            character_count,
            location_changes,
        )

        # Estimate duration based on complexity and scene type
        estimated_duration = self._estimate_duration(scene_type, complexity_score, total_words)

        # Ensure duration within limits
        estimated_duration = max(self.min_duration, min(self.max_duration, estimated_duration))

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
                "dialogue_ratio": dialogue_lines / max(1, total_words / 10),  # rough ratio
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
                    if next_line.startswith("(") or (len(next_line) > 0 and not next_line.startswith("#")):
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
                if len(name) > 2 and not name.startswith("SCENE") and not name.startswith("ACTION"):
                    characters.add(name)

        return len(characters)

    def _count_location_changes(self, text: str) -> int:
        """Count location changes based on scene headers."""
        # Look for scene headers like "INT. LOCATION - TIME"
        # Match lines that start with INT., EXT., or INT/EXT. followed by location and time
        scene_pattern = r"^(?:INT\.|EXT\.|INT/EXT\.)\s+[^-]+-\s*[^-]+$"
        matches = re.findall(scene_pattern, text, re.MULTILINE | re.IGNORECASE)
        return len(matches)

    def _classify_scene_type(self, dialogue_lines: int, action_density: float, total_words: int) -> SceneType:
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

    def _estimate_duration(self, scene_type: SceneType, complexity_score: float, total_words: int) -> int:
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

    def extract_characters(self, script_content: str) -> List[CharacterInfo]:
        """
        Extract character information from script content.

        Args:
            script_content: Full script text in markdown format

        Returns:
            List of CharacterInfo objects with visual tags and AI prompts
        """
        characters: Dict[str, CharacterInfo] = {}
        lines = script_content.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()

            # Look for character names in bold **CHARACTER NAME**
            bold_match = re.match(r"^\*\*([A-Z][A-Za-z\s]+)\*\*$", line)
            if bold_match and len(bold_match.group(1)) > 1:
                name = bold_match.group(1).strip()
                # Skip if it's a scene heading or generic term
                skip_words = {
                    "SCENE",
                    "INT",
                    "EXT",
                    "ACTION",
                    "DIALOGUE",
                    "SUMMARY",
                }
                if name.upper() not in skip_words and len(name) > 1:
                    # Look for description in surrounding context
                    description = self._extract_character_description(lines, i, name)
                    characters[name] = CharacterInfo(
                        name=name,
                        visual_tags=self._generate_visual_tags(name, description),
                        first_appearance=self._find_first_scene(lines, i),
                        role=self._infer_character_role(name, description, len(characters)),
                        appearance_description=description,
                        ai_prompt=self._generate_character_ai_prompt(name, description),
                    )

        return list(characters.values())

    def _extract_character_description(self, lines: List[str], name_index: int, name: str) -> str:
        """Extract character description from context around the name."""
        # Look for description after the character name
        description_parts = []

        # Check next few lines for description
        for j in range(name_index + 1, min(name_index + 5, len(lines))):
            line = lines[j].strip()
            if not line or line.startswith("#") or line.startswith("**"):
                break
            if line.startswith("(") and line.endswith(")"):
                description_parts.append(line[1:-1])
            elif ":" in line or "—" in line:
                desc = line.split(":", 1)[-1].split("—", 1)[-1].strip()
                if desc and len(desc) > 5:
                    description_parts.append(desc)

        return " ".join(description_parts)[:500]  # Limit description length

    def _find_first_scene(self, lines: List[str], char_index: int) -> str:
        """Find the scene where character first appears."""
        for i in range(char_index - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("###") or re.match(r"^(?:INT|EXT)", line, re.IGNORECASE):
                # Found scene header, extract scene name
                clean = re.sub(r"^#+\s*", "", line)
                return clean[:100]
        return "Unknown Scene"

    def _infer_character_role(self, name: str, description: str, existing_count: int) -> CharacterRole:
        """Infer character role from name and description."""
        desc_lower = description.lower()
        name.upper()

        # Check for protagonist indicators
        protagonist_words = [
            "hero",
            "protagonist",
            "main",
            "leader",
            "主角",
            "英雄",
        ]
        if any(word in desc_lower for word in protagonist_words):
            return CharacterRole.PROTAGONIST

        # Check for antagonist indicators
        antagonist_words = [
            "villain",
            "enemy",
            "antagonist",
            "evil",
            "反派",
            "敌人",
            "恶魔",
        ]
        if any(word in desc_lower for word in antagonist_words):
            return CharacterRole.ANTAGONIST

        # First character is usually protagonist
        if existing_count == 0:
            return CharacterRole.PROTAGONIST

        return CharacterRole.SUPPORTING

    def _generate_visual_tags(self, name: str, description: str) -> List[str]:
        """Generate visual tags for character anchor generation."""
        tags = []

        # Extract visual attributes from description
        hair_match = re.search(
            r"\b(long|short|black|brown|blonde|red|white|blue|purple|pink|green)\s+hair\b",
            description,
            re.IGNORECASE,
        )
        if hair_match:
            tags.append(f"{hair_match.group(1)} hair")

        age_match = re.search(
            r"\b(young|middle-aged|old|teen|youth|adult|child)\b",
            description,
            re.IGNORECASE,
        )
        if age_match:
            tags.append(age_match.group(1))

        gender_match = re.search(r"\b(woman|man|girl|boy|male|female)\b", description, re.IGNORECASE)
        if gender_match:
            tags.append(gender_match.group(1))

        clothing_match = re.search(
            r"\b(traditional|modern|casual|formal|ancient|fantasy)\s+",
            description,
            re.IGNORECASE,
        )
        if clothing_match:
            tags.append(clothing_match.group(1))

        if not tags:
            tags.append("anime style")

        return tags

    def _generate_character_ai_prompt(self, name: str, description: str) -> str:
        """Generate English AI prompt for character anchor image."""
        prompt_parts = []

        # Gender/age
        age_match = re.search(r"\b(young|middle-aged|old|teen)\b", description, re.IGNORECASE)
        gender_match = re.search(r"\b(woman|man|girl|boy)\b", description, re.IGNORECASE)

        if age_match and gender_match:
            prompt_parts.append(f"A {age_match.group(1)} {gender_match.group(1)}")
        elif gender_match:
            prompt_parts.append(f"A {gender_match.group(1)}")
        else:
            prompt_parts.append("A character")

        # Hair
        hair_match = re.search(
            r"\b(long|short|black|brown|blonde|red|white|blue|purple|pink)\s+hair\b",
            description,
            re.IGNORECASE,
        )
        if hair_match:
            prompt_parts.append(f"with {hair_match.group(1)} hair")

        # Clothing
        clothing_match = re.search(
            r"\b(traditional|modern|casual|formal|ancient|fantasy)\s+",
            description,
            re.IGNORECASE,
        )
        if clothing_match:
            prompt_parts.append(f"wearing {clothing_match.group(1)} clothing")

        # Style
        prompt_parts.append("anime style")
        prompt_parts.append("full body portrait")
        prompt_parts.append("clean background")

        return ", ".join(prompt_parts)

    def extract_scenes(self, script_content: str) -> List[SceneInfo]:
        """
        Extract scene information from script content.

        Args:
            script_content: Full script text in markdown format

        Returns:
            List of SceneInfo objects with settings and visual requirements
        """
        scenes: List[SceneInfo] = []
        lines = script_content.split("\n")

        current_scene_name = ""
        current_scene_lines = []
        scene_characters: List[str] = []

        for _i, line in enumerate(lines):
            stripped = line.strip()

            # Detect scene header
            scene_header_match = re.match(
                r"^(?:INT\.|EXT\.|INT/EXT\.)\s+(.+?)\s*-\s*(.+)$",
                stripped,
                re.IGNORECASE,
            )
            if scene_header_match:
                # Save previous scene if exists
                if current_scene_name:
                    scenes.append(
                        self._create_scene_info(
                            current_scene_name,
                            current_scene_lines,
                            scene_characters,
                        )
                    )

                # Start new scene
                location = scene_header_match.group(1).strip()
                time_of_day = scene_header_match.group(2).strip()
                current_scene_name = f"{location} - {time_of_day}"
                current_scene_lines = [line]
                scene_characters = []
            elif stripped.startswith("###") and current_scene_name:
                # Section header within scene
                current_scene_lines.append(line)
            elif stripped.startswith("**") and not stripped.endswith("**"):
                # Possible character name in context
                current_scene_lines.append(line)

        # Don't forget last scene
        if current_scene_name:
            scenes.append(self._create_scene_info(current_scene_name, current_scene_lines, scene_characters))

        return scenes

    def _create_scene_info(self, scene_name: str, lines: List[str], characters: List[str]) -> SceneInfo:
        """Create a SceneInfo object from collected lines."""
        full_text = "\n".join(lines)

        # Determine scene type
        is_interior = scene_name.upper().startswith("INT")
        scene_type = ProfessionalSceneType.INTERIOR if is_interior else ProfessionalSceneType.EXTERIOR

        # Extract mood/requirements
        mood_keywords = self._extract_scene_mood(full_text)
        visual_requirements = ", ".join(mood_keywords)

        # Estimate duration from content
        estimated_duration = max(
            self.min_duration,
            min(self.max_duration, len(lines) * 2),
        )

        return SceneInfo(
            scene_name=scene_name,
            setting=scene_name,
            scene_type=scene_type,
            duration=estimated_duration,
            characters=list(set(characters)),
            visual_requirements=visual_requirements,
            key_elements=self._extract_key_elements(full_text),
            ai_prompt=self._generate_scene_ai_prompt(scene_name, visual_requirements),
        )

    def _extract_scene_mood(self, text: str) -> List[str]:
        """Extract mood/atmosphere keywords from scene text."""
        mood_patterns = {
            "紧张": "tense",
            "温馨": "warm",
            "悲伤": "sad",
            "欢快": "cheerful",
            "神秘": "mysterious",
            "浪漫": "romantic",
            "黑暗": "dark",
            "明亮": "bright",
            "昏暗": "dim",
            "柔和": "soft",
            "激烈": "intense",
            "平静": "peaceful",
            "悬疑": "suspenseful",
            "喜剧": "comedic",
        }

        moods = []
        for cn, en in mood_patterns.items():
            if cn in text:
                moods.append(en)

        if not moods:
            moods.append("neutral")

        return moods

    def _extract_key_elements(self, text: str) -> List[str]:
        """Extract key props/elements from scene description."""
        elements = []

        # Look for bracketed descriptions
        brackets = re.findall(r"\[([^\]]+)\]", text)
        for bracket in brackets[:5]:  # Limit to 5 elements
            if len(bracket) > 3 and len(bracket) < 50:
                elements.append(bracket)

        return elements

    def _generate_scene_ai_prompt(self, setting: str, mood: str) -> str:
        """Generate English AI prompt for scene reference image."""
        # Parse setting components
        parts = setting.split(" - ")
        location = parts[0] if parts else setting
        time = parts[1] if len(parts) > 1 else "day"

        # Determine lighting from time of day
        lighting_map = {
            "day": "bright natural lighting",
            "night": "dark with artificial lighting",
            "morning": "soft morning light",
            "evening": "warm evening light",
            "afternoon": "golden afternoon light",
            "dawn": "soft dawn light",
            "dusk": "dramatic dusk lighting",
        }

        lighting = "natural lighting"
        time_lower = time.lower()
        for key, val in lighting_map.items():
            if key in time_lower:
                lighting = val
                break

        prompt = f"{location}, {lighting}, {mood} atmosphere, anime background style, wide shot"
        return prompt

    def generate_visual_prompts(
        self,
        characters: List[CharacterInfo],
        scenes: List[SceneInfo],
    ) -> Dict[str, str]:
        """
        Generate visual prompts for all scenes based on characters and scene info.

        Args:
            characters: List of character information
            scenes: List of scene information

        Returns:
            Dictionary mapping scene_name to AI visual prompt
        """
        prompts = {}
        char_dict = {c.name: c for c in characters}

        for scene in scenes:
            prompt_parts = [scene.ai_prompt]

            # Add characters in scene
            scene_chars = [c for c in scene.characters if c in char_dict]
            if scene_chars:
                char_names = ", ".join(scene_chars[:3])  # Max 3 characters
                prompt_parts.append(f"Characters: {char_names}")

            prompts[scene.scene_name] = "\n".join(prompt_parts)

        return prompts

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
