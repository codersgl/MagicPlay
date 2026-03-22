"""
Pytest configuration and fixtures for MagicPlay tests.

Provides:
- Test settings with mocked API keys
- Mock services for LLM, Image, and Video APIs
- Mock generators
- Common test utilities
"""

import sys
from pathlib import Path
from typing import List

import pytest

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import mocks for type hints and fixtures
from test.mocks import (
    MockCharacterGenerator,
    MockImageService,
    MockLLMService,
    MockScriptGenerator,
    MockVideoGenerator,
    MockVideoService,
)

from magicplay.config import Settings
from magicplay.generators.base import GenerationContext

# =============================================================================
# Test Settings
# =============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """
    Create test settings with mocked API keys.

    Returns:
        Settings instance for testing
    """
    return Settings(
        deepseek_api_key="test-deepseek-key",
        dashscope_api_key="test-dashscope-key",
        log_level="DEBUG",
        max_retry_attempts=1,  # Fast tests - no retries
        default_video_duration=5,
        enable_caching=False,
        enable_experiments=False,
    )


@pytest.fixture
def production_settings() -> Settings:
    """
    Create settings from actual environment.

    Returns:
        Settings instance from environment
    """
    from magicplay.config import get_settings

    return get_settings()


# =============================================================================
# Mock Services
# =============================================================================


@pytest.fixture
def mock_llm_service(test_settings: Settings) -> MockLLMService:
    """
    Create mock LLM service for testing.

    Returns:
        MockLLMService instance
    """
    return MockLLMService(test_settings)


@pytest.fixture
def mock_image_service(test_settings: Settings) -> MockImageService:
    """
    Create mock image service for testing.

    Returns:
        MockImageService instance
    """
    return MockImageService(test_settings)


@pytest.fixture
def mock_video_service(test_settings: Settings) -> MockVideoService:
    """
    Create mock video service for testing.

    Returns:
        MockVideoService instance
    """
    return MockVideoService(test_settings)


# =============================================================================
# Mock Generators
# =============================================================================


@pytest.fixture
def mock_script_generator(
    test_settings: Settings, mock_llm_service: MockLLMService
) -> MockScriptGenerator:
    """
    Create mock script generator for testing.

    Returns:
        MockScriptGenerator instance
    """
    return MockScriptGenerator(test_settings, mock_llm_service)


@pytest.fixture
def mock_character_generator(
    test_settings: Settings, mock_image_service: MockImageService
) -> MockCharacterGenerator:
    """
    Create mock character generator for testing.

    Returns:
        MockCharacterGenerator instance
    """
    return MockCharacterGenerator(test_settings, mock_image_service)


@pytest.fixture
def mock_video_generator(
    test_settings: Settings, mock_video_service: MockVideoService
) -> MockVideoGenerator:
    """
    Create mock video generator for testing.

    Returns:
        MockVideoGenerator instance
    """
    return MockVideoGenerator(test_settings, mock_video_service)


# =============================================================================
# Mock Comic Generators
# =============================================================================


@pytest.fixture
def mock_dynamic_panel_selector():
    """Mock DynamicPanelSelector for testing without LLM calls."""
    from unittest.mock import MagicMock

    from magicplay.generators.dynamic_panel_selector import (
        DynamicPanelSelector,
        PanelInfo,
    )

    mock = MagicMock(spec=DynamicPanelSelector)
    mock.analyze.return_value = [
        PanelInfo(
            panel_number=1,
            description="Test panel",
            dialogue="Hello!",
            composition="close-up",
            emotion="happy",
        )
    ]
    return mock


@pytest.fixture
def mock_comic_panel_generator(tmp_path):
    """Mock ComicPanelGenerator for testing without API calls."""
    from unittest.mock import MagicMock

    from magicplay.generators.comic_panel_gen import ComicPanelGenerator, PanelOutput

    mock = MagicMock(spec=ComicPanelGenerator)
    mock.generate_panel.return_value = PanelOutput(
        panel_number=1,
        image_path=tmp_path / "panel_001.png",
        description="Test panel",
        dialogue="Hello!",
        success=True,
    )
    return mock


# =============================================================================
# Test Directories
# =============================================================================


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """
    Create temporary test data directory.

    Args:
        tmp_path: Pytest temporary path

    Returns:
        Path to test data directory
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def test_output_dir(tmp_path: Path) -> Path:
    """
    Create temporary test output directory.

    Args:
        tmp_path: Pytest temporary path

    Returns:
        Path to test output directory
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def test_story_dir(test_data_dir: Path) -> Path:
    """
    Create test story directory structure.

    Args:
        test_data_dir: Test data directory fixture

    Returns:
        Path to test story directory
    """
    story_dir = test_data_dir / "story" / "test_story"
    story_dir.mkdir(parents=True, exist_ok=True)
    return story_dir


@pytest.fixture
def sample_story_bible() -> str:
    """
    Sample story bible content for testing.

    Returns:
        Sample story bible text
    """
    return """
# Story Bible: Test Story

## Character Profiles

### **张三**:
- 身份：年轻企业家
- 人设类型：霸总、外冷内热
- 性格特征：冷静、果断、内心柔软
- ai 演员锚点：黑色短发，深邃眼眸，深色西装

### **李四**:
- 身份：职场新人
- 人设类型：小白花、成长型
- 性格特征：善良、坚韧、乐观
- ai 演员锚点：长发及腰，温柔眼神，简约连衣裙

## Cinematic Style Guide

- 色彩基调：暖色调，金色和蓝色对比
- 光影氛围：电影感 lighting，戏剧性阴影
- 场景风格：现代都市，高端办公室

## World Building

Setting: Modern Shanghai, financial district
Timeline: Contemporary
"""


@pytest.fixture
def sample_episode_outline() -> str:
    """
    Sample episode outline for testing.

    Returns:
        Sample episode outline text
    """
    return """
# Episode 1: First Meeting

## Scene Breakdown

### Scene 1: Office Introduction
- Location: CEO Office
- Characters: 张三
- Action: 张三 handles morning meetings

### Scene 2: First Encounter
- Location: Company Lobby
- Characters: 张三，李四
- Action: 李四 spills coffee on 张三

### Scene 3: Confrontation
- Location: Meeting Room
- Characters: 张三，李四，Manager
- Action: Discussion about the incident
"""


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def sample_generation_context() -> GenerationContext:
    """
    Create sample generation context for testing.

    Returns:
        GenerationContext with sample data
    """
    return GenerationContext(
        story_name="test_story",
        episode_name="episode_1",
        scene_name="scene_1",
        story_context="Test story context",
        episode_context="Test episode context",
        memory="Previous scene memory",
        scene_prompt="Test scene prompt",
    )


# =============================================================================
# Helper Functions for Tests
# =============================================================================


def create_test_video_file(path: Path, duration: float = 1.0) -> Path:
    """
    Create a minimal test video file.

    Args:
        path: Path to create video
        duration: Duration in seconds

    Returns:
        Path to created video
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def create_test_image_file(path: Path, size: tuple = (100, 100)) -> Path:
    """
    Create a minimal test image file.

    Args:
        path: Path to create image
        size: Image dimensions

    Returns:
        Path to created image
    """
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color="red")
    img.save(path)
    return path
