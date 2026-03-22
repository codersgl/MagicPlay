"""
Mock services and generators for testing.

Provides mock implementations of:
- LLM Service
- Image Service
- Video Service
- Script Generator
- Character Generator
- Video Generator
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

from magicplay.config import Settings
from magicplay.generators.base import (
    BaseGenerator,
    GenerationContext,
    GenerationResult,
)
from magicplay.ports.services import IImageService, ILLMService, IVideoService

# =============================================================================
# Mock LLM Service
# =============================================================================


class MockLLMService(ILLMService):
    """
    Mock LLM service for testing.

    Returns predefined responses or echoes prompts.
    """

    name = "mock_llm"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or Settings(deepseek_api_key="test-key", dashscope_api_key="test-key")
        self._healthy = True
        self.call_count = 0
        self.last_prompts: List[Dict[str, str]] = []

    def generate_content(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate mock response."""
        self.call_count += 1
        self.last_prompts.append({"system": system_prompt, "user": user_prompt})

        # Return predefined response if set
        if hasattr(self, "_mock_response"):
            return self._mock_response

        # Default: echo back user prompt with prefix
        return f"[MOCK LLM RESPONSE] {user_prompt[:100]}..."

    def set_mock_response(self, response: str) -> None:
        """Set mock response to return."""
        self._mock_response = response

    def health_check(self) -> bool:
        return self._healthy

    def set_healthy(self, healthy: bool) -> None:
        """Set health status."""
        self._healthy = healthy


# =============================================================================
# Mock Image Service
# =============================================================================


class MockImageService(IImageService):
    """
    Mock image service for testing.

    Creates placeholder image files.
    """

    name = "mock_image"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or Settings(deepseek_api_key="test-key", dashscope_api_key="test-key")
        self._healthy = True
        self.call_count = 0
        self.generated_images: List[Path] = []

    def generate_image(
        self,
        prompt: str,
        output_path: Union[str, Path],
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        guidance_scale: float = 7.5,
        **kwargs,
    ) -> Optional[Path]:
        """Create placeholder image file."""
        self.call_count += 1
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create placeholder image
        try:
            from PIL import Image

            img = Image.new("RGB", (min(width, 100), min(height, 100)), color="blue")
            img.save(output_path)
            self.generated_images.append(output_path)
            return output_path
        except ImportError:
            # PIL not available, create empty file
            output_path.touch()
            self.generated_images.append(output_path)
            return output_path

    def health_check(self) -> bool:
        return self._healthy

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy


# =============================================================================
# Mock Video Service
# =============================================================================


class MockVideoService(IVideoService):
    """
    Mock video service for testing.

    Creates placeholder video files.
    """

    name = "mock_video"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or Settings(deepseek_api_key="test-key", dashscope_api_key="test-key")
        self._healthy = True
        self.call_count = 0
        self.generated_videos: List[Path] = []

    def generate_video(
        self,
        prompt: str,
        output_path: Union[str, Path],
        reference_image: Optional[Union[str, Path]] = None,
        duration: int = 5,
        negative_prompt: Optional[str] = None,
        **kwargs,
    ) -> Optional[Path]:
        """Create placeholder video file."""
        self.call_count += 1
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()  # Create empty file
        self.generated_videos.append(output_path)
        return output_path

    def extract_last_frame(self, video_path: Union[str, Path], output_path: Union[str, Path]) -> Optional[Path]:
        """Create placeholder frame file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        return output_path

    def health_check(self) -> bool:
        return self._healthy

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy


# =============================================================================
# Mock Generators
# =============================================================================


class MockScriptGenerator(BaseGenerator[str]):
    """
    Mock script generator for testing.
    """

    name = "mock_script_generator"
    description = "Mock script generator for tests"

    def __init__(self, config: Settings, llm_service: Optional[ILLMService] = None):
        super().__init__(config)
        self.llm = llm_service or MockLLMService(config)
        self.call_count = 0
        self.generated_scripts: List[Path] = []

    def generate(self, context: GenerationContext) -> GenerationResult[str]:
        """Generate mock script."""
        self.call_count += 1

        # Create mock script file
        output_path = self.config.project_root / "data" / "test" / f"{context.scene_name}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"# Mock Script: {context.scene_name}\n\nThis is a test script."
        output_path.write_text(content, encoding="utf-8")
        self.generated_scripts.append(output_path)

        return self._wrap_success(output_path, context)

    def generate_story_outline(self, idea: str) -> str:
        return f"[MOCK] Story outline for: {idea}"

    def generate_episode_outline(self, story_context: str, episode_idea: str) -> str:
        return f"[MOCK] Episode outline for: {episode_idea}"

    def generate_scene_script(self, scene_name: str, **kwargs) -> Path:
        """Generate mock scene script."""
        self.call_count += 1
        output_path = self.config.project_root / "data" / "test" / f"{scene_name}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"# Mock Scene: {scene_name}\n\nTest content."
        output_path.write_text(content, encoding="utf-8")
        self.generated_scripts.append(output_path)
        return output_path

    def generate_visual_prompt(self, script_path: Union[str, Path]) -> str:
        return f"[MOCK] Visual prompt for: {script_path}"


class MockCharacterGenerator(BaseGenerator[Path]):
    """
    Mock character generator for testing.
    """

    name = "mock_character_generator"
    description = "Mock character generator for tests"

    def __init__(self, config: Settings, image_service: Optional[IImageService] = None):
        super().__init__(config)
        self.image_service = image_service or MockImageService(config)
        self.call_count = 0

    def generate(self, context: GenerationContext) -> GenerationResult[Path]:
        """Generate mock character image."""
        self.call_count += 1

        output_path = self.config.project_root / "data" / "test" / "character.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()

        return self._wrap_success(output_path, context)


class MockVideoGenerator(BaseGenerator[Path]):
    """
    Mock video generator for testing.
    """

    name = "mock_video_generator"
    description = "Mock video generator for tests"

    def __init__(self, config: Settings, video_service: Optional[IVideoService] = None):
        super().__init__(config)
        self.video_service = video_service or MockVideoService(config)
        self.call_count = 0

    def generate(self, context: GenerationContext) -> GenerationResult[Path]:
        """Generate mock video."""
        self.call_count += 1

        output_path = self.config.project_root / "data" / "test" / "video.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()

        return self._wrap_success(output_path, context)
