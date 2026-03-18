"""
Script Generator Module

Generates story outlines, episode outlines, and scene scripts.
"""

from pathlib import Path
from typing import Dict, Optional, Union

from magicplay.config import Settings
from magicplay.generators.base import BaseGenerator, GenerationContext, GenerationResult
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
        min_scene_length: int = 3000,
        max_scene_length: int = 10000,
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
            self.story_prompt_template = (self.prompts_dir / "gen_story.md").read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            self.story_prompt_template = fallback

        try:
            self.episode_prompt_template = (
                self.prompts_dir / "gen_episode.md"
            ).read_text(encoding="utf-8")
        except FileNotFoundError:
            self.episode_prompt_template = fallback

        try:
            self.scene_prompt_template = (
                self.prompts_dir / "gen_scene.md"
            ).read_text(encoding="utf-8")
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

    def generate_episode_outline(
        self,
        story_context: str,
        episode_idea: str
    ) -> str:
        """
        Generate a detailed episode outline.

        Args:
            story_context: Story bible context
            episode_idea: Episode idea/summary

        Returns:
            Generated episode outline content
        """
        system_prompt = self.episode_prompt_template
        user_prompt = (
            f"Story Context (Bible):\n{story_context}\n\n"
            f"Episode Idea/Summary:\n{episode_idea}"
        )

        if self.genre:
            user_prompt += f"\n\nGenre Focus: {self.genre}"

        return self.llm.generate_content(system_prompt, user_prompt)

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
        user_prompt = (
            f"请生成一个原创真人短剧剧本，字数限制{self.min_scene_length}~{self.max_scene_length}。"
        )

        if self.genre:
            user_prompt += (
                f"\n\n【风格要求 (Genre)】\n请严格遵循【{self.genre}】的风格进行创作。"
            )
        if self.reference_story:
            user_prompt += (
                f"\n\n【模仿参考 (Reference)】\n"
                f"请模仿【{self.reference_story}】的叙事风格、对话语气和剧情节奏。"
            )

        # Inject character profiles with Visual Tags (强制注入角色视觉档案)
        if character_profiles:
            character_section = "\n\n【角色档案 - Visual Tags 锚定 - 必须遵守】\n"
            character_section += "以下角色的 Visual Tags 必须在剧本中首次出场时**完整复述**，格式为：`角色名 [Visual Tags: ...]`\n\n"
            for char_name, visual_tags in character_profiles.items():
                character_section += f"- {visual_tags}\n"
            character_section += "\n**重要**：任何角色首次出场时，必须使用上述 Visual Tags 格式描述外貌特征！"
            user_prompt += character_section

        if memory:
            user_prompt = f"上集剧情回顾：【{memory}】。\n" + user_prompt
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
   - 生成高分辨率、清晰的视频画面，真实摄影质感。
   - 保持视觉细节丰富，纹理真实。
   - 确保光线和色彩的一致性，自然光照。
   - 避免画面模糊、失真或伪影。
   - 禁止动漫风格、3D 渲染风格、插画风格、游戏风格。

2. **内容一致性 (Content Consistency)**:
   - 场景元素在整个视频中保持稳定。
   - 背景环境连贯不突变。
   - 物体位置和大小关系合理，符合透视规律。
   - 时间线逻辑清晰。

3. **角色一致性 (Character Consistency)**:
   - 同一角色外貌特征保持不变（发色、瞳色、脸型）。
   - 服装、发型、配饰等细节严格一致。
   - 角色行为模式符合设定，动作自然真实。
   - 面部表情和肢体语言连贯，符合人体力学。

4. **剧情连贯性 (Plot Continuity)**:
   - 故事情节发展逻辑合理，动作序列流畅自然。
   - 情感变化有层次感。
   - 场景转换平滑过渡，符合物理规律。
   - 避免瞬间移动、不合逻辑的行为变化。

5. **物理真实性 (Physical Realism) - 关键要求**:
   - 所有动作、互动必须符合真实世界的物理规律。
   - 重力效果必须真实，物体不会无故漂浮。
   - 光影效果必须符合真实光照原理和阴影投射。
   - 人物动作必须符合人体解剖学和运动力学。
   - 材质纹理必须真实（金属反光、布料褶皱、皮肤质感）。
   - 透视关系必须正确，远近大小符合真实视觉。
   - 避免任何超现实、动漫式或游戏风格的夸张表现。
   - 确保角色与环境的互动物理合理（如脚步接触地面、物体碰撞等）。

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
            for char_name, visual_tags in character_profiles.items():
                character_section += f"- {visual_tags}\n"
            character_section += "\n**重要**：在视觉提示词中必须明确描述上述角色特征，确保生成视频中角色形象一致！"

        # Build visual style guidance
        style_guidance = ""
        if visual_style:
            style_guidance = f"\n\n【全剧视觉风格】\n{visual_style}"
        else:
            style_guidance = """\n\n【视觉风格指导】
- 风格：真人剧质感，Cinematic lighting, 8k resolution, photorealistic, film grain
- 色调：冷色调为主（蓝、青、银灰），营造悬疑科幻氛围
- 光影：善用侧光、逆光、明暗对比，避免平光
- 构图：多用纵深构图、过肩镜头、特写镜头增强沉浸感"""

        user_prompt = (
            f"请阅读以下网文真人剧剧本（悬疑科幻类型），并提炼成一段**中英混合**的视觉描述提示词（Visual Prompt）。\n\n"
            f"{content_standards}"
            f"{character_section}"
            f"{style_guidance}\n\n"
            f"## 任务要求 (Task Requirements)\n"
            f"1. **风格锁定**：开头必须包含明确的高质量风格词（如：'Cinematic lighting, 8k resolution, photorealistic, Masterpiece, 精致真人剧质感, film grain, natural skin texture'）。\n"
            f"2. **角色锚定**：必须提取并锁定角色的核心 Visual Tags（如发色、瞳色、具体服装细节），并在提示词中强调这些特征以确保一致性。\n"
            f"3. **场景细节**：详细描述环境、光影和氛围，确保背景与之前的场景一致。悬疑科幻类型善用冷色调、光影对比。\n"
            f"4. **动态描述**：描述清晰、连贯的动作，符合真实物理规律，避免产生歧义导致画面变形。\n"
            f"5. **负面提示 (Implicit)**：提示词应避免暗示模糊、低质量、动漫风格或不稳定的元素。\n"
            f"6. **格式**：输出一段描述性极强的自然语言提示词（Prompt），字数控制在 400 字左右，中英混合便于 AI 理解。\n\n"
            f"## 待处理剧本内容：\n{script_content}"
        )

        visual_prompt = self.llm.generate_content(
            system_prompt, user_prompt, temperature=0.7
        )
        return visual_prompt


# Import here to avoid circular dependency
from magicplay.services.llm import LLMService
