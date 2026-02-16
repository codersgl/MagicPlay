from pathlib import Path
from typing import Optional, Union

from magicplay.services.llm import LLMService


class ScriptGenerator:
    def __init__(
        self,
        output_dir: Union[str, Path],
        min_scene_length: int = 3000,
        max_scene_length: int = 10000,
        prompts_dir: Optional[Union[str, Path]] = None,
        genre: str = "",
        reference_story: str = "",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.min_scene_length = min_scene_length
        self.max_scene_length = max_scene_length
        self.llm = LLMService()
        self.genre = genre
        self.reference_story = reference_story

        if prompts_dir is None:
            # src/magicplay/prompts
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        # Ensure save directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load specific prompt templates
        try:
            self.story_prompt_template = (self.prompts_dir / "gen_story.md").read_text(
                encoding="utf-8"
            )
            self.episode_prompt_template = (
                self.prompts_dir / "gen_episode.md"
            ).read_text(encoding="utf-8")
            self.scene_prompt_template = (self.prompts_dir / "gen_scene.md").read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            # Fallback to generic prompt if specific files are missing
            print("Warning: Specific prompt files not found. Using generic prompt.")
            fallback_file = self.prompts_dir / "prompt1.md"
            fallback = (
                fallback_file.read_text(encoding="utf-8")
                if fallback_file.exists()
                else ""
            )
            self.story_prompt_template = fallback
            self.episode_prompt_template = fallback
            self.scene_prompt_template = fallback

    def generate_story_outline(self, idea: str) -> str:
        """
        Generate a comprehensive story bible and series arc based on an idea.
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
        Generate a detailed episode outline based on story context and episode idea.
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
    ) -> Path:
        """
        Generate a scene script.
        """

        # Construct System Prompt from scene template
        system_prompt = self.scene_prompt_template
        if story_context:
            system_prompt += f"\n\n【故事背景与世界观】\n{story_context}"
        if episode_context:
            system_prompt += f"\n\n【本集剧情大纲】\n{episode_context}"

        # Construct User Prompt
        user_prompt = f"请生成一个原创动画短片剧本，字数限制{self.min_scene_length}~{self.max_scene_length}。"

        if self.genre:
            user_prompt += (
                f"\n\n【风格要求 (Genre)】\n请严格遵循【{self.genre}】的风格进行创作。"
            )
        if self.reference_story:
            user_prompt += f"\n\n【模仿参考 (Reference)】\n请模仿【{self.reference_story}】的叙事风格、对话语气和剧情节奏。"

        if memory:
            user_prompt = f"上集剧情回顾：【{memory}】。\n" + user_prompt
        if scene_prompt:
            user_prompt += f"\n\n【本场剧情要求】\n{scene_prompt}"

        # Call Agent
        result = self.llm.generate_content(system_prompt, user_prompt)

        # Save Result
        if not result:
            raise RuntimeError("Failed to generate scene content (empty result)")

        file_path = self.output_dir / f"{scene_name}.md"
        with open(file_path, "w", encoding="utf_8") as f:
            f.write(result)

        print(f"Scene script generated: {file_path}")
        return file_path

    def generate_visual_prompt(self, script_path: Union[str, Path]) -> str:
        """
        Summarize the script into a visual prompt for video generation.
        """
        script_path = Path(script_path)
        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")

        script_content = script_path.read_text(encoding="utf-8")

        system_prompt = "你是专业的AI动漫视觉导演，擅长编制能生成高质量、连贯一致视频的提示词（Prompt Engineering）。"

        # Incorporate the specific standards requested by the user
        content_standards = """
## 质量标准要求 (Quality Standards)
1. **视频质量优化 (Video Quality)**：
   - 生成高分辨率、清晰的视频画面。
   - 保持视觉细节丰富，纹理真实。
   - 确保光线和色彩的一致性。
   - 避免画面模糊、失真或伪影。
2. **内容一致性 (Content Consistency)**：
   - 场景元素在整个视频中保持稳定。
   - 背景环境连贯不突变。
   - 物体位置和大小关系合理。
   - 时间线逻辑清晰。
3. **角色一致性 (Character Consistency)**：
   - 同一角色外貌特征保持不变（发色、瞳色、脸型）。
   - 服装、发型、配饰等细节严格一致。
   - 角色行为模式符合设定。
   - 面部表情和肢体语言连贯。
4. **剧情连贯性 (Plot Continuity)**：
   - 故事情节发展逻辑合理，动作序列流畅自然。
   - 情感变化有层次感。
   - 场景转换平滑过渡。
"""

        user_prompt = (
            f"请阅读以下网文漫改剧本，并提炼成一段**中文**的视觉描述提示词（Visual Prompt）。\n\n"
            f"{content_standards}\n\n"
            f"## 任务要求 (Task Requirements)\n"
            f"1. **风格锁定**：开头必须包含明确的高质量风格词（如：'Cinematic lighting, 8k resolution, Unreal Engine 5 render, Masterpiece, 精致国漫风'）。\n"
            f"2. **角色锚定**：必须提取并锁定角色的核心Visual Tags（如发色、瞳色、具体服装细节），并在提示词中强调这些特征以确保一致性。\n"
            f"3. **场景细节**：详细描述环境、光影和氛围，确保背景与之前的场景一致。\n"
            f"4. **动态描述**：描述清晰、连贯的动作，避免产生歧义导致画面变形。\n"
            f"5. **负面提示 (Implicit)**：提示词应避免暗示模糊、低质量或不稳定的元素。\n"
            f"6. **格式**：输出一段描述性极强的自然语言提示词（Prompt），字数控制在 300字左右。\n\n"
            f"## 待处理剧本内容：\n{script_content}"
        )

        visual_prompt = self.llm.generate_content(
            system_prompt, user_prompt, temperature=0.7
        )
        return visual_prompt
