# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

```bash
# Install dependencies (requires Python >= 3.13)
uv sync

# Run all tests
uv run pytest

# Run specific test file
uv run pytest test/test_script_analyzer.py -v

# Run tests with coverage
uv run pytest --cov=magicplay --cov-report=html

# Code formatting
uv run black src/magicplay test
uv run isort src/magicplay test

# Linting
uv run flake8 src/magicplay test

# Type checking
uv run mypy src/magicplay --ignore-missing-imports

# Run generation pipeline
uv run scripts/run.py --story "MyStory" --episode "01_EpisodeOne"
uv run scripts/run.py --story "MyStory" --run-all

# Run Streamlit UI (requires ui extras: uv sync --all-packages)
uv run streamlit run src/magicplay/app.py
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--story` | str | Required | Name of the story folder |
| `--episode` | str | Series1 | Episode folder name |
| `--scenes` | int | 5 | Number of scenes per episode |
| `--run-all` | flag | False | Process all episodes in story |
| `--genre` | str | "" | Genre (e.g., Xuanhuan, Xiuxian, Sci-Fi) |
| `--reference-story` | str | "" | Reference story for style guidance |
```
```

## Environment Setup

Create a `.env` file in the project root:

```
DEEPSEEK_API_KEY=your_api_key_here
DASHSCOPE_API_KEY=your_api_key_here
```

The `.env` file is automatically gitignored - never commit API keys.

## Key Conventions

- **Paths**: Always use `pathlib.Path` for file system operations, not string concatenation
- **Imports**: Use absolute imports (e.g., `from magicplay.utils.paths import DataManager`)
- **Path Management**: Always use `DataManager` from `magicplay.utils.paths` for resolving paths to data, scripts, and video outputs. Never hardcode paths.
- **Package Name**: Use `magicplay`, not typos like `magicpaly`
- **Prompts**: Stored as Markdown files in `src/magicplay/prompts/`

## Architecture Overview

MagicPlay is an AI-powered automated short play script and video generation tool. The system uses a **three-phase optimization architecture** to address character consistency, video quality, and long scene stability.

### Core Architecture Patterns

1. **Orchestrator Pattern**: Central coordination via `Orchestrator` (single episode) and `StoryOrchestrator` (full story)
2. **Generator Pattern**: Specialized content generators extending `BaseGenerator`
3. **Service Pattern**: External API abstractions (LLM, Image, Video) extending `BaseService`
4. **Manager Pattern**: State and consistency management (`StoryConsistencyManager`)
5. **Three-Phase Optimization**: Progressive enhancement strategy for quality improvement

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layer                       │
│  Settings (Pydantic) | Exceptions | Logging                 │
├─────────────────────────────────────────────────────────────┤
│                    Interface Layer (Ports)                   │
│  IGenerator | ILLMService | IImageService | IVideoService   │
├─────────────────────────────────────────────────────────────┤
│                      Service Layer                           │
│  LLMService | ImageService | VideoService | BaseService     │
├─────────────────────────────────────────────────────────────┤
│                    Generator Layer                           │
│  ScriptGenerator | CharacterGenerator | VideoGenerator      │
├─────────────────────────────────────────────────────────────┤
│                   Orchestration Layer                        │
│  Orchestrator | OptimizedOrchestrator | StoryOrchestrator   │
├─────────────────────────────────────────────────────────────┤
│                   Supporting Modules                         │
│  Analyzer | Consistency | Evaluator | Workflow | Registry   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Config → StoryOrchestrator → Orchestrator
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
Phase 1:      Phase 2:        Phase 3:
Character     Unified         Multi-frame
Consistency   Generation      Segmentation
    ↓               ↓               ↓
Character     Scene           Video
Anchors       Concepts        Segments
    └───────────────┼───────────────┘
                    ↓
          Final Video Output
```

## Key Modules

### `src/magicplay/core/`
- `orchestrator.py`: Main `Orchestrator` class coordinating episode generation
- `optimized_orchestrator.py`: Enhanced orchestrator with quality evaluation, caching, and workflow engine

### `src/magicplay/generators/`
- `base.py`: `BaseGenerator` abstract class with common generation logic
- `script_gen.py`: `ScriptGenerator` for story/episode/scene script generation
- `video_gen.py`: `VideoGenerator` using Dashscope API
- `character_gen.py`: `CharacterImageGenerator` for Phase 1 consistency
- `scene_concept_gen.py`: Scene concept image generation
- `scene_segment_gen.py`: Multi-frame scene segmentation (Phase 3)

### `src/magicplay/services/`
- `base.py`: `BaseService` abstract class with logging and health checks
- `llm.py`: `LLMService` using DeepSeek API (OpenAI-compatible client)
- `image_api.py`: Image generation via Dashscope
- `video_api.py`: Video generation via Dashscope Wan2.6-t2v model

### `src/magicplay/ports/`
Interface definitions for dependency inversion:
- `generators.py`: `IGenerator` protocol
- `services.py`: `ILLMService`, `IImageService`, `IVideoService` protocols
- `repositories.py`: `IRepository` protocol

### `src/magicplay/analyzer/`
- `script_analyzer.py`: `ScriptAnalyzer` for script analysis and duration estimation

### `src/magicplay/consistency/`
- `story_consistency.py`: `StoryConsistencyManager` for character consistency across scenes

### `src/magicplay/utils/`
- `paths.py`: `DataManager` for path management
- `media.py`: `MediaUtils` for video stitching and frame extraction
- `retry.py`: `api_retry` and `with_fallback` decorators
- `cache.py`: `SimpleCache` with TTL support
- `validators.py`: Validation utilities

### `src/magicplay/di_container.py`
Dependency injection container using `dependency-injector` library.

## Configuration

Configuration is managed via `src/magicplay/config/settings.py` using Pydantic Settings:

```python
from magicplay.config import get_settings

settings = get_settings()
# Access: settings.deepseek_api_key, settings.dashscope_api_key, etc.
```

Environment variables (via `.env` file):
- `DEEPSEEK_API_KEY`: Required for script generation
- `DASHSCOPE_API_KEY`: Required for video/image generation

## Testing

Tests use pytest with fixtures defined in `test/conftest.py` and mocks in `test/mocks.py`:

```python
# Mock services available via fixtures
def test_something(mock_llm_service, mock_script_generator):
    # mock_llm_service: MockLLMService
    # mock_script_generator: MockScriptGenerator
    pass
```

Key test fixtures:
- `test_settings`: Test configuration with mocked API keys
- `mock_llm_service`, `mock_image_service`, `mock_video_service`: Mock services
- `mock_script_generator`, `mock_character_generator`, `mock_video_generator`: Mock generators
- `sample_story_bible`, `sample_episode_outline`: Sample data
- Located in: `test/conftest.py` (fixtures) and `test/mocks.py` (mock classes)

## Dependency Injection

The DI container (`di_container.py`) provides wired dependencies:

```python
from magicplay.di_container import Container

container = Container()
script_gen = container.script_generator()
llm_service = container.llm_service()
```

## Three-Phase Optimization

### Phase 1: Character Consistency
- Pre-generate character anchor images from story bible
- Ensures visual consistency across scenes/episodes
- Output: `data/story/{StoryName}/character_anchors/`

### Phase 2: Unified Generation
- Always use image-to-video (i2v) mode with concept images as references
- Consistent quality across all scenes
- Output: `data/story/{StoryName}/{EpisodeName}/scene_concepts/`

### Phase 3: Multi-frame Segmentation
- For scenes > 8 seconds, generate multiple key frames
- Create video segments between key moments
- Stitch segments for higher quality
- Output: `data/story/{StoryName}/{EpisodeName}/scene_segments/`

## Common Development Patterns

### Adding a New Generator

```python
from magicplay.generators.base import BaseGenerator, GenerationContext, GenerationResult

class MyGenerator(BaseGenerator[Path]):
    name = "my_generator"
    description = "Description of what this generates"

    def generate(self, context: GenerationContext) -> GenerationResult[Path]:
        # Implementation
        return self._wrap_success(output_path, context)
```

### Adding a New Service

```python
from magicplay.services.base import BaseService
from magicplay.ports.services import IMyService

class MyService(BaseService, IMyService):
    name = "my_service"

    def __init__(self, config: Settings):
        super().__init__(config)
        # Initialize client

    def health_check(self) -> bool:
        # Implementation
```

### Using Retry Decorator

```python
from magicplay.utils.retry import api_retry

@api_retry(max_attempts=3, base_delay=1.0)
def my_api_call():
    # Implementation
```

### Using Cache

```python
from magicplay.utils.cache import SimpleCache, memoize

cache = SimpleCache(ttl=3600)

@memoize(cache, key_fn=lambda x, y: f"{x}:{y}")
def expensive_function(x, y):
    # Implementation
```

## Gotchas

- Video generation may fail if scene duration exceeds model limits (~10 seconds)
- Phase 3 segmentation is automatically triggered for scenes > 8 seconds
- Use `DataManager` for ALL path operations - never hardcode paths

## Important Paths

```
MagicPlay/
├── src/magicplay/          # Source code
│   └── prompts/            # Prompt templates (Markdown)
├── data/                   # Generated data
│   └── story/
│       └── {StoryName}/
│           ├── story_bible.md
│           ├── character_anchors/
│           └── {EpisodeName}/
│               ├── generated_scripts/
│               ├── scene_concepts/
│               └── scene_segments/
├── videos/                 # Generated videos
│   └── {StoryName}/
│       └── {EpisodeName}/
├── test/                   # Test suite
└── scripts/run.py          # CLI entry point
```
