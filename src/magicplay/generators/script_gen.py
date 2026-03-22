"""
Script Generator Module

Generates story outlines, episode outlines, and scene scripts.
"""

from pathlib import Path
from typing import Dict, Optional, Union

from magicplay.config import Settings
from magicplay.generators.base import (
    BaseGenerator,
    GenerationContext,
    GenerationResult,
)
from magicplay.ports.services import ILLMService


class ScriptGenerator(BaseGenerator[str]):
    """
    Generator for story bibles, episode outlines, and scene scripts.

    Features:
    - Story bible generation from core idea
    - Episode outline generation from story context
    - Scene script generation with memory support
    - Visual prompt extraction for video generation
    """

    name = "script_generator"
    description = "Generates scripts and outlines for video production"

    def __init__(
        self,
        config: Optional[Settings] = None,
        llm_service: Optional[ILLMService] = None,
        output_dir: Optional[Union[str, Path]] = None,
        min_scene_length: int = 600,
        max_scene_length: int = 2000,
        prompts_dir: Optional[Union[str, Path]] = None,
        genre: str = "",
        reference_story: str = "",
    ):
        """
        Initialize script generator.

        Args:
            config: Application settings
            llm_service: LLM service instance
            output_dir: Directory for generated scripts
            min_scene_length: Minimum scene length in characters
            max_scene_length: Maximum scene length in characters
            prompts_dir: Directory containing prompt templates
            genre: Genre/style for generation
            reference_story: Reference story for tone imitation
        """
        if config is None:
            from magicplay.config import get_settings

            config = get_settings()

        super().__init__(config)

        self.llm = llm_service or LLMService(config)
        self.output_dir = Path(output_dir) if output_dir else None
        self.min_scene_length = min_scene_length
        self.max_scene_length = max_scene_length
        self.genre = genre
        self.reference_story = reference_story

        # Load prompt templates
        if prompts_dir is None:
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        self._load_prompt_templates()

        # Ensure output directory exists
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_prompt_templates(self) -> None:
        """Load prompt templates from files."""
        fallback_file = self.prompts_dir / "prompt1.md"
        fallback = (
            fallback_file.read_text(encoding="utf-8")
            if fallback_file.exists()
            else "You are a professional screenwriter."
        )

        try:
            self.story_prompt_template = (self.prompts_dir / "gen_story.md").read_text(encoding="utf-8")
        except FileNotFoundError:
            self.story_prompt_template = fallback

        try:
            self.episode_prompt_template = (self.prompts_dir / "gen_episode.md").read_text(encoding="utf-8")
        except FileNotFoundError:
            self.episode_prompt_template = fallback

        try:
            self.scene_prompt_template = (self.prompts_dir / "gen_scene.md").read_text(encoding="utf-8")
        except FileNotFoundError:
            self.scene_prompt_template = fallback

    def generate(self, context: GenerationContext) -> GenerationResult[str]:
        """
        Generate a scene script from context.

        Args:
            context: Generation context

        Returns:
            GenerationResult with script path
        """
        try:
            self.pre_generate_hook(context)

            # Validate context
            error = self._validate_context(context)
            if error:
                return self._wrap_error(error, context)

            # Generate script
            result = self.generate_scene_script(
                scene_name=context.scene_name or "scene_1",
                story_context=context.story_context,
                episode_context=context.episode_context,
                memory=context.memory,
                scene_prompt=context.scene_prompt,
            )

            self.post_generate_hook(context, GenerationResult(success=True, data=result))
            return self._wrap_success(result, context)

        except Exception as e:
            self.logger.error(f"Script generation failed: {e}")
            return self._wrap_error(str(e), context)

    def generate_story_outline(self, idea: str) -> str:
        """
        Generate a comprehensive story bible and series arc.

        Args:
            idea: Core story idea

        Returns:
            Generated story bible content
        """
        system_prompt = self.story_prompt_template
        user_prompt = f"Here is the core idea for the series:\n{idea}"

        if self.genre:
            user_prompt += f"\n\nStory Genre/Style: {self.genre}"
        if self.reference_story:
            user_prompt += f"\n\nReference/Tone Imitation: {self.reference_story}"

        return self.llm.generate_content(system_prompt, user_prompt)

    def generate_episode_outline(self, story_context: str, episode_idea: str) -> str:
        """
        Generate a detailed episode outline.

        Args:
            story_context: Story bible context
            episode_idea: Episode idea/summary

        Returns:
            Generated episode outline content
        """
        system_prompt = self.episode_prompt_template
        user_prompt = f"Story Context (Bible):\n{story_context}\n\nEpisode Idea/Summary:\n{episode_idea}"

        if self.genre:
            user_prompt += f"\n\nGenre Focus: {self.genre}"

        return self.llm.generate_content(system_prompt, user_prompt)

    def split_outline_into_scenes(self, episode_outline: str) -> list[str]:
        """
        Parse and split an episode outline into a list of individual scene prompts.

        Args:
            episode_outline: The full markdown episode outline.

        Returns:
            A list of string prompts, one for each scene.
        """
        system_prompt = (
            "You are a professional screenwriter assistant. Your task is to take a full episode outline "
            "and extract each scene into a distinct scene prompt.\n\n"
            "Output FORMAT:\n"
            "For each scene, output exactly in this format separated by '---SCENE_BREAK---':\n"
            "Scene X: [Scene Name]\n"
            "Setting: [Location]\n"
            "Plot Beats: [What happens in this scene, specific actions and dialogue hints]\n"
            "---SCENE_BREAK---\n\n"
            "Ensure ALL scenes mentioned in the outline are extracted. Do NOT invent new scenes."
        )
        user_prompt = (
            f"Here is the episode outline:\n\n{episode_outline}\n\nPlease split it into individual scene prompts."
        )
        result = self.llm.generate_content(system_prompt, user_prompt)

        if not result:
            return []

        scenes = [s.strip() for s in result.split("---SCENE_BREAK---") if s.strip()]
        return scenes

    def generate_scene_script(
        self,
        scene_name: str,
        story_context: str = "",
        episode_context: str = "",
        memory: str = "",
        scene_prompt: str = "",
        character_profiles: Optional[Dict[str, str]] = None,
    ) -> Path:
        """
        Generate a scene script and save to file.

        Args:
            scene_name: Name/identifier for the scene
            story_context: Story bible context
            episode_context: Episode outline context
            memory: Previous scene memory for continuity
            scene_prompt: Specific scene requirements
            character_profiles: Dictionary mapping character names to formatted Visual Tags

        Returns:
            Path to generated script file
        """
        # Construct System Prompt
        system_prompt = self.scene_prompt_template
        if story_context:
            system_prompt += f"\n\n【故事背景与世界观】\n{story_context}"
        if episode_context:
            system_prompt += f"\n\n【本集剧情大纲】\n{episode_context}"

        # Construct User Prompt
        user_prompt = f"请生成一个原创真人短剧剧本，字数限制{self.min_scene_length}~{self.max_scene_length}。"

        if self.genre:
            user_prompt += f"\n\n【风格要求 (Genre)】\n请严格遵循【{self.genre}】的风格进行创作。"
        if self.reference_story:
            user_prompt += (
                f"\n\n【模仿参考 (Reference)】\n请模仿【{self.reference_story}】的叙事风格、对话语气和剧情节奏。"
            )

        # Inject character profiles with Visual Tags (强制注入角色视觉档案)
        if character_profiles:
            character_section = "\n\n【角色档案 - Visual Tags 锚定 - 必须遵守】\n"
            character_section += (
                "以下角色的 Visual Tags 必须在剧本中首次出场时**完整复述**，格式为：`角色名 [Visual Tags: ...]`\n\n"
            )
            for _char_name, visual_tags in character_profiles.items():
                character_section += f"- {visual_tags}\n"
            character_section += "\n**重要**：任何角色首次出场时，必须使用上述 Visual Tags 格式描述外貌特征！"
            user_prompt += character_section

        if memory:
            continuity_block = (
                "## 前场状态交接 - 必须严格遵守以下衔接要求\n"
                "下一场景**必须**从此状态自然延续，不得出现人物位置/外貌/道具/场景的断层：\n\n"
                f"{memory}\n\n"
                "---\n\n"
            )
            user_prompt = continuity_block + user_prompt
        if scene_prompt:
            user_prompt += f"\n\n【本场剧情要求】\n{scene_prompt}"

        # Call LLM
        result = self.llm.generate_content(system_prompt, user_prompt)

        if not result:
            raise RuntimeError("Failed to generate scene content (empty result)")

        # Save to file
        file_path = self.output_dir / f"{scene_name}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(result, encoding="utf-8")

        self.logger.info(f"Scene script generated: {file_path}")
        return file_path

    def generate_visual_prompt(
        self,
        script_path: Union[str, Path],
        character_profiles: Optional[Dict[str, str]] = None,
        visual_style: Optional[str] = "",
        previous_visual_key: Optional[str] = None,
    ) -> str:
        """
        Summarize a script into a visual prompt for video generation.

        Enhanced for sci-fi/suspense genre:
        - Inject character Visual Tags for consistency
        - Add genre-specific visual style guidance
        - Emphasize physical realism and lighting

        Args:
            script_path: Path to script file
            character_profiles: Optional dictionary of character Visual Tags
            visual_style: Optional global visual style string

        Returns:
            Visual prompt string
        """
        script_path = Path(script_path)
        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")

        script_content = script_path.read_text(encoding="utf-8")

        system_prompt = (
            "你是专业的 AI 真人剧视觉导演，擅长编制能生成高质量、连贯一致、"
            "符合物理规律视频的提示词（Prompt Engineering）。"
            "特别擅长悬疑科幻类型的视觉呈现，善用光影对比、冷色调、科技感元素。"
        )

        content_standards = """
## 质量标准要求 (Quality Standards)
1. **视频质量优化 (Video Quality)**:
   - 生成高分辨率、清晰的动漫风格视频画面。
   - 保持视觉细节丰富，动漫纹理和线条清晰。
   - 确保光线和色彩的一致性，动漫光影风格。
   - 避免画面模糊、失真或伪影。
   - 必须保持动漫风格，避免写实摄影风格。

2. **内容一致性 (Content Consistency)**:
   - 场景元素在整个视频中保持稳定。
   - 背景环境连贯不突变。
   - 物体位置和大小关系合理，符合动漫透视规律。
   - 时间线逻辑清晰。

3. **角色一致性 (Character Consistency)**:
   - 同一角色外貌特征保持不变（发色、瞳色、脸型）。
   - 服装、发型、配饰等细节严格一致。
   - 角色行为模式符合设定，动作符合动漫风格。
   - 面部表情和肢体语言连贯，符合动漫表现规律。

4. **剧情连贯性 (Plot Continuity)**:
   - 故事情节发展逻辑合理，动作序列流畅自然。
   - 情感变化有层次感。
   - 场景转换平滑过渡，符合叙事规律。
   - 避免瞬间移动、不合逻辑的行为变化。

5. **动漫物理规律 (Anime Physics) - 关键要求**:
   - 所有动作、互动符合动漫世界的物理规律。
   - 重力效果可以有适当的动漫式夸张。
   - 光影效果采用动漫光影风格，阴影投射更具风格化。
   - 人物动作可以有动态pose和角度。
   - 材质纹理采用动漫风格（金属反光、布料褶皱、头发质感）。
   - 透视关系可以稍有夸张以增强视觉冲击。
   - 允许适度的动漫式夸张表现。
   - 确保角色与环境的互动具有动漫风格的协调感。

6. **悬疑科幻类型专用 (Sci-Fi/Suspense Specific)**:
   - 善用光影对比（Chiaroscuro lighting）营造悬疑氛围。
   - 冷色调为主（蓝、青、银灰），适当使用霓虹色点缀。
   - 科技感元素需详细描述（全息投影、智能界面、未来交通工具）。
   - 纵深构图增强空间感和神秘感。
"""

        # Build character consistency section
        character_section = ""
        if character_profiles:
            character_section = "\n\n【角色 Visual Tags - 必须保持一致】\n"
            for _char_name, visual_tags in character_profiles.items():
                character_section += f"- {visual_tags}\n"
            character_section += "\n**重要**：在视觉提示词中必须明确描述上述角色特征，确保生成视频中角色形象一致！"

        # Build visual style guidance
        style_guidance = ""
        if visual_style:
            style_guidance = f"\n\n【全剧视觉风格】\n{visual_style}"
        else:
            style_guidance = """\n\n【视觉风格指导】
- 风格：动漫质感，Anime style, cel shaded, vibrant colors, clean lineart
- 色调：冷色调为主（蓝、青、银灰），营造悬疑科幻氛围
- 光影：善用侧光、逆光、明暗对比，避免平光
- 构图：多用纵深构图、过肩镜头、特写镜头增强沉浸感"""

        user_prompt = (
            f"请阅读以下网文动漫剧本（悬疑科幻类型），并提炼成一段**中英混合**的视觉描述提示词（Visual Prompt）。\n\n"
            f"{content_standards}"
            f"{character_section}"
            f"{style_guidance}\n\n"
            f"## 任务要求 (Task Requirements)\n"
            f"1. **风格锁定**：开头必须包含明确的高质量动漫风格词（如：\n"
            f"   'Anime style, cel shaded, vibrant colors, clean lineart, soft shading, masterpiece'）。\n"
            f"2. **角色锚定**：必须提取并锁定角色的核心 Visual Tags（如发色、瞳色、\n"
            f"   具体服装细节），并在提示词中强调这些特征以确保一致性。\n"
            f"3. **场景细节**：详细描述环境、光影和氛围，确保背景与之前的场景一致。悬疑科幻类型善用冷色调、光影对比。\n"
            f"4. **动态描述**：描述清晰、连贯的动作，符合动漫物理规律，避免产生歧义导致画面变形。\n"
            f"5. **负面提示 (Implicit)**：提示词应避免暗示写实风格、低质量或不稳定的元素。\n"
            f"6. **格式**：输出一段描述性极强的自然语言提示词（Prompt），\n"
            f"   字数控制在 400 字左右，中英混合便于 AI 理解。\n\n"
            f"## 待处理剧本内容：\n{script_content}"
        )

        # R1: First try to extract VISUAL KEY directly from the script (faster, no LLM call)
        visual_key = _extract_visual_key_from_script(script_content)
        if visual_key:
            self.logger.info("VISUAL KEY extracted from script (skipping LLM call)")
            # Prepend quality standard tags so the video API always gets them
            quality_prefix = (
                "Anime style, cel shaded, vibrant colors, clean lineart, soft shading, masterpiece, best quality. "
            )

            # Add visual continuity instruction if previous scene's visual key is provided
            continuity_instruction = ""
            if previous_visual_key:
                continuity_instruction = (
                    f"\n\n【视觉连续性 - 必须遵守】\n"
                    f"延续上一场景的视觉风格：色调、光影方向、空间布局必须与之一致。\n"
                    f"上一场景视觉关键词：{previous_visual_key[:300]}"
                )

            # Append character Visual Tags for consistency anchoring
            if character_profiles:
                char_tags = "; ".join(character_profiles.values())
                visual_key = f"{quality_prefix}{visual_key}{continuity_instruction}\n\n角色 Visual Tags: {char_tags}"
            else:
                visual_key = f"{quality_prefix}{visual_key}{continuity_instruction}"
            return visual_key

        # R1 fallback: VISUAL KEY not found in script, call LLM to generate visual prompt
        self.logger.info("VISUAL KEY not found in script, falling back to LLM generation")

        # Add visual continuity instruction if previous scene's visual key is provided
        if previous_visual_key:
            continuity_block = (
                f"\n\n【视觉连续性 - 必须遵守】\n"
                f"延续上一场景的视觉风格：色调、光影方向、空间布局必须与之一致。\n"
                f"上一场景视觉关键词：{previous_visual_key[:300]}"
            )
            user_prompt += continuity_block

        visual_prompt = self.llm.generate_content(system_prompt, user_prompt, temperature=0.7)
        return visual_prompt


import re as _re  # noqa: E402

# Import here to avoid circular dependency
from magicplay.services.llm import LLMService  # noqa: E402


def _extract_visual_key_from_script(script_content: str) -> Optional[str]:
    """
    Extract the VISUAL KEY block from a generated scene script.

    The gen_scene.md prompt produces a `### 2. VISUAL KEY` section whose
    content is wrapped in a ```visual_key ... ``` fenced code block.
    Falls back to searching for an un-fenced `## 2. VISUAL KEY` section as well.

    Args:
        script_content: Raw markdown content of the scene script.

    Returns:
        The extracted visual key string, or None if not found.
    """
    # Strategy 1: fenced ```visual_key ... ``` block (preferred, from updated prompt)
    fenced_match = _re.search(
        r"```visual_key\s*\n(.*?)\n```",
        script_content,
        _re.DOTALL | _re.IGNORECASE,
    )
    if fenced_match:
        return fenced_match.group(1).strip()

    # Strategy 2: Generic fenced block just after a header containing "VISUAL KEY"
    # Handles: ## 2. VISUAL KEY ... ```...```
    header_fenced_match = _re.search(
        r"##[#]?\s*(?:\d+\.\s*)?VISUAL KEY[^\n]*\n+```[^\n]*\n(.*?)\n```",
        script_content,
        _re.DOTALL | _re.IGNORECASE,
    )
    if header_fenced_match:
        return header_fenced_match.group(1).strip()

    # Strategy 3: Plain text under VISUAL KEY header up to next ## heading
    plain_match = _re.search(
        r"##[#]?\s*(?:\d+\.\s*)?VISUAL KEY[^\n]*\n+(.*?)(?=\n##[#]?\s|\Z)",
        script_content,
        _re.DOTALL | _re.IGNORECASE,
    )
    if plain_match:
        text = plain_match.group(1).strip()
        if text:
            return text

    return None


def extract_scene_exit_state(script_content: str) -> str:
    """
    Extract a compact structured summary of the final state of a scene script.

    This summary is injected as the "memory" header for the next scene so that
    the LLM can reliably continue the story from where the previous scene ended.

    Extracted elements (in order of priority):
    1. SCENE HEADER  — location / time
    2. VISUAL KEY    — visual tone and character appearance (first 250 chars)
    3. Visual Tags   — character appearance tags found in the script body
    4. Last action   — the final non-blank, non-heading line of the script body

    Args:
        script_content: Raw markdown content of the scene script.

    Returns:
        A structured summary string (~300 chars max), suitable for memory injection.
    """
    parts: list[str] = []

    # 1. SCENE HEADER (e.g. "INT. LABORATORY - NIGHT")
    header_match = _re.search(
        r"^((?:INT\.|EXT\.)[^\n]+)",
        script_content,
        _re.MULTILINE | _re.IGNORECASE,
    )
    if header_match:
        parts.append(f"[场所/时间] {header_match.group(1).strip()}")

    # 2. VISUAL KEY — take first 250 chars to capture color/lighting/character look
    visual_key = _extract_visual_key_from_script(script_content)
    if visual_key:
        parts.append(f"[视觉基调] {visual_key[:250].strip()}")

    # 3. Character Visual Tags lines (format: "角色名 [Visual Tags: ...]")
    tag_matches = _re.findall(
        r"[\u4e00-\u9fa5\w]+\s*\[Visual Tags:[^\]]+\]",
        script_content,
        _re.IGNORECASE,
    )
    if tag_matches:
        parts.append("[角色外貌] " + " | ".join(tag_matches[:3]))

    # 4. Last meaningful action/dialogue line of the script body (after VISUAL KEY section)
    # Strip heading lines (start with #) and blank lines, take the last non-empty line
    body_lines = [
        ln.strip()
        for ln in script_content.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#") and not ln.lstrip().startswith("```")
    ]
    if body_lines:
        parts.append(f"[末尾动作] {body_lines[-1][:120]}")

    if not parts:
        # Absolute fallback: first 300 chars
        return script_content[:300].strip()

    return "\n".join(parts)
