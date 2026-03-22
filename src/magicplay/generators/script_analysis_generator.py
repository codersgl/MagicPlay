"""
Script Analysis Generator for Professional Workflow Phase 1.

Orchestrates LLM-based script analysis to extract characters, scenes,
and generate detailed AI prompts for the professional 6-stage workflow.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from magicplay.analyzer.script_analyzer import ScriptAnalyzer
from magicplay.schema.professional_workflow import (
    CharacterInfo,
    CharacterRole,
    SceneInfo,
)
from magicplay.schema.professional_workflow import SceneType as ProfessionalSceneType
from magicplay.schema.professional_workflow import (
    ScriptAnalysisResult,
)
from magicplay.services.llm import LLMService


class ScriptAnalysisGenerator:
    """
    Orchestrates comprehensive script analysis using LLM with structured output.

    This generator combines rule-based extraction (via ScriptAnalyzer) with
    LLM-based analysis for more nuanced character/scene understanding.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the script analysis generator.

        Args:
            llm_service: Optional LLM service for enhanced analysis.
                        If not provided, uses default LLMService.
        """
        self._llm_service = llm_service or LLMService()
        self._script_analyzer = ScriptAnalyzer()

    def analyze(self, script_content: str) -> ScriptAnalysisResult:
        """
        Analyze script content comprehensively.

        Uses a hybrid approach:
        1. Rule-based extraction for basic character/scene info
        2. LLM-based extraction for detailed visual prompts and reasoning

        Args:
            script_content: Full script text in markdown format

        Returns:
            ScriptAnalysisResult with characters, scenes, and visual prompts
        """
        if not script_content:
            logger.warning("Empty script content provided")
            return ScriptAnalysisResult(
                characters=[],
                scenes=[],
                total_duration=0,
                reasoning="Empty script content",
            )

        # Phase 1: Rule-based extraction
        logger.info("Extracting characters and scenes (rule-based)...")
        characters = self._script_analyzer.extract_characters(script_content)
        scenes = self._script_analyzer.extract_scenes(script_content)

        # Phase 2: LLM-enhanced analysis for visual prompts
        logger.info("Enhancing analysis with LLM...")
        enhanced_result = self._llm_enhanced_analysis(
            script_content, characters, scenes
        )

        # Merge results
        if enhanced_result:
            characters = enhanced_result.get("characters", characters)
            scenes = enhanced_result.get("scenes", scenes)

        # Generate visual prompts
        visual_prompts = self._script_analyzer.generate_visual_prompts(
            characters, scenes
        )

        # Calculate total duration
        total_duration = sum(s.duration for s in scenes)

        return ScriptAnalysisResult(
            characters=characters,
            scenes=scenes,
            total_duration=total_duration,
            visual_style="anime",  # Default, could be enhanced with LLM
            reasoning=f"Extracted {len(characters)} characters and {len(scenes)} scenes",
        )

    def _llm_enhanced_analysis(
        self,
        script_content: str,
        rule_based_characters: List[CharacterInfo],
        rule_based_scenes: List[SceneInfo],
    ) -> Optional[Dict]:
        """
        Use LLM to enhance character/scene extraction with detailed AI prompts.

        Args:
            script_content: Original script content
            rule_based_characters: Characters extracted by rule-based method
            rule_based_scenes: Scenes extracted by rule-based method

        Returns:
            Enhanced dictionaries for characters and scenes, or None on failure
        """
        try:
            prompt = self._build_llm_analysis_prompt(
                script_content, rule_based_characters, rule_based_scenes
            )

            system_prompt = (
                "You are a professional AI short drama script analyst. "
                "Analyze the provided script and extract structured information."
            )

            response = self._llm_service.generate_content(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=4000,
            )

            return self._parse_llm_response(
                response, rule_based_characters, rule_based_scenes
            )

        except Exception as e:
            logger.warning(f"LLM-enhanced analysis failed: {e}")
            return None

    def _build_llm_analysis_prompt(
        self,
        script_content: str,
        characters: List[CharacterInfo],
        scenes: List[SceneInfo],
    ) -> str:
        """Build the LLM analysis prompt."""
        char_names = [c.name for c in characters]
        scene_names = [s.scene_name for s in scenes]

        prompt = f"""Analyze this script and provide detailed character and scene information.

## Characters Found:
{', '.join(char_names) if char_names else 'None detected'}

## Scenes Found:
{', '.join(scene_names) if scene_names else 'None detected'}

## Script Content:
{script_content[:3000]}...

## Your Task:
1. For each character, provide:
   - Detailed appearance description (hair, clothing, features)
   - Personality traits
   - English AI image generation prompt for character reference

2. For each scene, provide:
   - Detailed visual environment description
   - Mood/atmosphere keywords
   - English AI image generation prompt for scene reference

3. Suggest overall visual style (anime/realistic/illustrated)

## Output Format (JSON):
{{
    "characters": [
        {{
            "name": "Character Name",
            "appearance": "Detailed description...",
            "personality": ["trait1", "trait2"],
            "ai_prompt": "English prompt for image generation..."
        }}
    ],
    "scenes": [
        {{
            "name": "Scene Name",
            "description": "Detailed visual description...",
            "mood": ["mood1", "mood2"],
            "ai_prompt": "English prompt for image generation..."
        }}
    ],
    "visual_style": "anime/realistic/etc."
}}
"""
        return prompt

    def _parse_llm_response(
        self,
        response: str,
        fallback_characters: List[CharacterInfo],
        fallback_scenes: List[SceneInfo],
    ) -> Optional[Dict]:
        """Parse LLM JSON response into structured data."""
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            # Parse characters
            characters = []
            for char_data in data.get("characters", []):
                # Match with fallback by name similarity
                matched = self._match_character_by_name(
                    char_data.get("name", ""), fallback_characters
                )
                if matched:
                    # Update with LLM-enhanced data
                    matched.appearance_description = char_data.get("appearance", "")
                    matched.personality_traits = char_data.get("personality", [])
                    matched.ai_prompt = char_data.get("ai_prompt", matched.ai_prompt)
                    characters.append(matched)
                else:
                    # New character from LLM
                    characters.append(
                        CharacterInfo(
                            name=char_data.get("name", "Unknown"),
                            visual_tags=[],
                            first_appearance="",
                            role=CharacterRole.SUPPORTING,
                            appearance_description=char_data.get("appearance", ""),
                            personality_traits=char_data.get("personality", []),
                            ai_prompt=char_data.get("ai_prompt", ""),
                        )
                    )

            # Parse scenes
            scenes = []
            for scene_data in data.get("scenes", []):
                matched = self._match_scene_by_name(
                    scene_data.get("name", ""), fallback_scenes
                )
                if matched:
                    # Update with LLM-enhanced data
                    matched.visual_requirements = ", ".join(scene_data.get("mood", []))
                    matched.ai_prompt = scene_data.get("ai_prompt", matched.ai_prompt)
                    scenes.append(matched)
                else:
                    scenes.append(
                        SceneInfo(
                            scene_name=scene_data.get("name", "Unknown"),
                            setting=scene_data.get("name", ""),
                            scene_type=ProfessionalSceneType.INTERIOR,
                            duration=10,
                            characters=[],
                            visual_requirements=", ".join(scene_data.get("mood", [])),
                            ai_prompt=scene_data.get("ai_prompt", ""),
                        )
                    )

            return {"characters": characters, "scenes": scenes}

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return None

    def _match_character_by_name(
        self, name: str, fallback_characters: List[CharacterInfo]
    ) -> Optional[CharacterInfo]:
        """Match LLM character name to fallback character by similarity."""
        name_lower = name.lower()
        for char in fallback_characters:
            if name_lower in char.name.lower() or char.name.lower() in name_lower:
                return char
        return None

    def _match_scene_by_name(
        self, name: str, fallback_scenes: List[SceneInfo]
    ) -> Optional[SceneInfo]:
        """Match LLM scene name to fallback scene by similarity."""
        name_lower = name.lower()
        for scene in fallback_scenes:
            scene_lower = scene.scene_name.lower()
            if name_lower in scene_lower or scene_lower in name_lower:
                return scene
            return None

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON string from LLM response."""
        import re

        # Try direct parsing first
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Look for JSON in code blocks
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to find JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        return text

    def analyze_file(self, script_path: str) -> Optional[ScriptAnalysisResult]:
        """
        Analyze script from file.

        Args:
            script_path: Path to script file

        Returns:
            ScriptAnalysisResult or None on failure
        """
        try:
            path = Path(script_path)
            if not path.exists():
                logger.error(f"Script file not found: {script_path}")
                return None

            content = path.read_text(encoding="utf-8")
            return self.analyze(content)
        except Exception as e:
            logger.error(f"Failed to analyze script file: {e}")
            return None

    def save_analysis_report(
        self, result: ScriptAnalysisResult, output_path: Path
    ) -> Path:
        """
        Save analysis result as a markdown report.

        Args:
            result: ScriptAnalysisResult to save
            output_path: Path to save the report

        Returns:
            Path to saved report
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# 剧本分析报告 (Script Analysis Report)",
            "",
            f"**总时长**: {result.total_duration}秒",
            f"**人物数量**: {len(result.characters)}",
            f"**场景数量**: {len(result.scenes)}",
            f"**视觉风格**: {result.visual_style}",
            "",
            "---",
            "",
            "## 人物清单 (Character List)",
            "",
        ]

        for i, char in enumerate(result.characters, 1):
            lines.extend(
                [
                    f"### {i}. {char.name}",
                    f"- **角色**: {char.role.value}",
                    f"- **外貌描述**: {char.appearance_description}",
                    f"- **性格特点**: {', '.join(char.personality_traits)}",
                    f"- **AI生图提示词**:",
                    f"```",
                    char.ai_prompt,
                    "```",
                    "",
                ]
            )

        lines.extend(
            [
                "---",
                "",
                "## 场景清单 (Scene List)",
                "",
            ]
        )

        for i, scene in enumerate(result.scenes, 1):
            lines.extend(
                [
                    f"### {i}. {scene.scene_name}",
                    f"- **场景类型**: {scene.scene_type.value}",
                    f"- **时长**: {scene.duration}秒",
                    f"- **出场人物**: {', '.join(scene.characters)}",
                    f"- **视觉要求**: {scene.visual_requirements}",
                    f"- **AI生图提示词**:",
                    f"```",
                    scene.ai_prompt,
                    "```",
                    "",
                ]
            )

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Analysis report saved to: {output_path}")

        return output_path
