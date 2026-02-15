from pathlib import Path
from typing import Optional, Union

from magicplay.utils.paths import DataManager
from magicplay.services.llm import LLMService


class ScriptGenerator:
    def __init__(
        self,
        output_dir: Union[str, Path],
        min_scene_length: int = 3000,
        max_scene_length: int = 10000,
        prompts_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.min_scene_length = min_scene_length
        self.max_scene_length = max_scene_length
        self.llm = LLMService()

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

        system_prompt = "你是专业的视觉导演。你的任务是将剧本转化为视频生成模型（Text-to-Video）可理解的提示词。"
        user_prompt = (
            f"请阅读以下剧本，并提炼成一段英文的视觉描述提示词（Visual Prompt）。\n"
            f"要求：\n"
            f"1. 包含具体的场景描述、光影氛围、镜头语言。\n"
            f"2. 描述主要角色的外观和动作。\n"
            f"3. 纯英文输出，不要包含解释性文字。\n"
            f"4. 长度控制在 300-500 words。\n\n"
            f"剧本内容：\n{script_content}"
        )

        visual_prompt = self.llm.generate_content(
            system_prompt, user_prompt, temperature=0.7
        )
        return visual_prompt
