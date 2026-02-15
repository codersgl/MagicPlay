import os
import time
from pathlib import Path
from typing import Optional, Union

from openai import OpenAI

from magicplay.utils import Utils


class ScenesPromptGenerator:
    def __init__(
        self,
        min_scene_length: int = 3000,
        max_scene_length: int = 10000,
        api_provider: str = "deepseek",
        prompts_dir: Optional[Union[str, Path]] = None,
        save_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.api_provider = api_provider
        self.min_scene_length = min_scene_length
        self.max_scene_length = max_scene_length

        if prompts_dir is None:
            # src/magicplay/prompts
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        if save_path is None:
            # Project Root / data / scenes
            # __file__ = src/magicplay/scene_generate/content.py
            # parent.parent.parent.parent = Project Root
            self.save_path = Path(__file__).parents[3] / "data" / "scenes"
        else:
            self.save_path = Path(save_path)

        # Ensure save directory exists
        self.save_path.mkdir(parents=True, exist_ok=True)

        self.prompt = Utils.get_prompt(self.prompts_dir)

    def generate_scene(self) -> Path:
        result = ""
        if self.api_provider == "deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": f"{self.prompt}"},
                    {
                        "role": "user",
                        "content": f"请生成一个原创动画短片剧本, 字数限制{self.min_scene_length}~{self.max_scene_length}",
                    },
                ],
                stream=False,
            )

            result = (
                response.choices[0].message.content
                if response.choices[0].message.content
                else ""
            )

        if not result:
            raise RuntimeError("Failed to generate scene content (empty result)")

        try:
            timestamp = int(time.time())
            scene_path = self.save_path / f"scene_{timestamp}.md"
            with open(scene_path, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"scene generated and saved to: {scene_path}")
            return scene_path
        except Exception as e:
            raise RuntimeError(f"Failed to write result file: {e}")
