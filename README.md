# MagicPlay

MagicPlay is an automated content generation tool that creates **真人爽文短剧** scripts and accompanying videos using advanced AI models. The system features a three-phase optimization architecture that addresses character consistency, video quality, and long scene stability in AI-generated **真人剧** content.

## 🎬 Showcase

<https://github.com/user-attachments/assets/ad2bcb82-cfe9-42ed-9d62-32d4830128f9>

## ✨ Core Features

- **Story Generation**: Generate complete story outlines with multiple episodes using LLMs (DeepSeek).
- **Scene Generation**: Creates creative short play scripts with detailed scene descriptions.
- **Video Generation**: Produces video content based on generated scenes using Aliyun Dashscope (Wan2.6-t2v model).
- **Batch Processing**: Run all episodes in a story sequentially with a single command.
- **Three-Phase Optimization**: Advanced architecture addressing key challenges in AI video generation:
  - **Phase 1**: Character consistency pre-generation
  - **Phase 2**: Unified video generation mode
  - **Phase 3**: Multi-frame scene segmentation

## 🏗️ Project Architecture

### System Overview

MagicPlay employs a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     User Configuration                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  StoryOrchestrator                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                    Orchestrator                     │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │  │
│  │  │    Phase 1  │ │    Phase 2  │ │    Phase 3  │  │  │
│  │  │  Character  │ │   Unified   │ │   Multi-    │  │  │
│  │  │  Consistency│ │  Generation │ │   Frame     │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                     Output Pipeline                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │  Scripts    │ │   Images    │ │   Videos    │          │
│  │  (.md)      │ │ (PNG/JPG)   │ │   (.mp4)    │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Project Structure

```
MagicPlay/
├── src/magicplay/          # Source code
│   ├── core/               # Orchestration logic
│   │   ├── orchestrator.py       # Single episode orchestrator
│   │   └── story_orchestrator.py # Full story orchestrator
│   ├── generators/         # Content generators
│   │   ├── script_gen.py         # Script generation
│   │   ├── video_gen.py          # Video generation (unified mode)
│   │   ├── character_gen.py      # Character anchor images (Phase 1)
│   │   ├── scene_concept_gen.py  # Scene concept images (Phase 2)
│   │   └── scene_segment_gen.py  # Multi-frame generation (Phase 3)
│   ├── analyzer/           # Content analysis
│   │   └── script_analyzer.py    # Script analysis & duration estimation
│   ├── consistency/        # Consistency management
│   │   └── story_consistency.py  # Story consistency manager
│   ├── services/          # External API services
│   │   ├── llm.py                # DeepSeek API integration
│   │   ├── video_api.py          # Aliyun Dashscope video API
│   │   └── image_api.py          # Image generation API
│   ├── prompts/           # Prompt templates
│   │   ├── gen_story.md          # Story generation template
│   │   ├── gen_episode.md        # Episode generation template
│   │   └── gen_scene.md          # Scene generation template
│   └── utils/             # Utility modules
│       ├── paths.py              # Path management (DataManager)
│       └── media.py              # Media processing utilities
├── data/                  # Generated data
│   └── story/             # Story-specific data hierarchy
│       └── {StoryName}/
│           ├── story_bible.md           # Story bible
│           ├── character_anchors/       # Character images (Phase 1)
│           └── {EpisodeName}/
│               ├── generated_scripts/   # Generated scripts
│               ├── scene_concepts/      # Concept images (Phase 2)
│               └── scene_segments/      # Segment data (Phase 3)
├── videos/                # Generated videos
│   └── {StoryName}/
│       └── {EpisodeName}/
│           ├── scene_1.mp4              # Individual scenes
│           ├── scene_2.mp4
│           └── {EpisodeName}_full.mp4   # Stitched episode
└── scripts/
    └── run.py              # Entry point script
```

## 🚀 Three-Phase Optimization Architecture

### Phase 1: Character Consistency Pre-generation
**Problem**: Character appearance inconsistency across scenes and episodes
**Solution**: Pre-generate character anchor images at story initialization
**Implementation**:
- `CharacterImageGenerator`: Generates high-quality character portraits based on story bible descriptions
- `StoryConsistencyManager`: Manages character information and image references
- Automatic integration in `Orchestrator`: Generates character images before scene generation begins
**Benefits**: 
  - Consistent character appearance throughout the story
  - Visual reference for video generation models
  - Reusable character assets across episodes
**Output**: `data/story/{StoryName}/character_anchors/`

### Phase 2: Unified Video Generation Mode
**Problem**: Inconsistent video generation quality between first and subsequent scenes
**Solution**: Always use image-to-video (i2v) model with concept images as references
**Implementation**:
- `SceneConceptGenerator`: Generates concept images (first frames) for each scene
- `VideoGenerator` unified mode: Forces i2v generation even for first scenes
- Enhanced visual prompt generation with character consistency guidance
**Benefits**:
  - Consistent video quality across all scenes
  - Better control over initial scene composition
  - Reduced dependency on frame-by-frame continuity errors
**Output**: `data/story/{StoryName}/{EpisodeName}/scene_concepts/`

### Phase 3: Multi-frame Scene Segmentation
**Problem**: Long scenes suffer from quality degradation and inconsistency
**Solution**: Multi-frame generation with key moment anchoring
**Implementation**:
- `SceneSegmentGenerator`: Analyzes scenes to identify key moments (beginning, middle, end)
- Generates concept images for each key moment
- Creates video segments between key moments using i2v
- Stitches segments for higher quality output
**Trigger Condition**: Scene duration > 8 seconds (configurable)
**Benefits**:
  - Higher quality for longer scenes
  - Better narrative pacing control
  - Reduced cumulative errors in long sequences
**Output**: `data/story/{StoryName}/{EpisodeName}/scene_segments/`

## 📊 Data Flow

```
1. User Configuration
   │
   ├── Story selection
   ├── Episode specification  
   ├── Genre/style preferences
   └── Reference story guidance
   │
2. Story Orchestration
   │
   ├── Load story context (story bible)
   ├── Phase 1: Generate character anchor images
   └── Iterate through episodes
   │
3. Episode Processing (Per Episode)
   │
   ├── Load episode context/outline
   ├── Determine scenes to process
   └── For each scene:
       │
       ├── Script Generation
       │   ├── Generate scene script using LLM
       │   ├── Update memory for continuity
       │   └── Save to generated_scripts/
       │
       ├── Script Analysis
       │   ├── Analyze complexity and word count
       │   ├── Determine scene type (dialogue/action/mixed)
       │   └── Estimate optimal video duration
       │
       ├── Visual Prompt Generation
       │   └── Convert script to visual description
       │
       ├── Phase 2: Scene Concept Generation
       │   ├── Generate concept image (first frame)
       │   └── Save to scene_concepts/
       │
       ├── Video Generation Decision
       │   ├── If duration > 8s: Use Phase 3 (multi-frame)
       │   └── Else: Use Phase 2 (single-frame)
       │
       ├── [Phase 3] Multi-frame Generation
       │   ├── Analyze script for key moments
       │   ├── Generate key moment images
       │   ├── Generate video segments
       │   └── Stitch segments together
       │
       ├── [Phase 2] Single-frame Generation
       │   └── Generate video using concept image as reference
       │
       └── Save video to videos/
   │
4. Final Processing
   │
   ├── Stitch scene videos into complete episode
   ├── Optionally stitch episodes into full story
   └── Save final output
```

## 🛠️ Prerequisites

- **Python**: >= 3.13 (managed via `uv`)
- **API Keys**: Set the following environment variables (can be loaded via a `.env` file):
  - `DEEPSEEK_API_KEY`: For script generation (via OpenAI client).
  - `DASHSCOPE_API_KEY`: For video generation (via Aliyun Dashscope).

## 📦 Installation

This project uses `uv` for dependency management.

```bash
uv sync
```

## 🚀 Usage

### Command Line Interface

To run the generation pipeline, use the `scripts/run.py` entry point via `uv`.

#### 1. Basic Generation

**Generate a Single Episode:**

```bash
uv run scripts/run.py --story "MyStory" --episode "01_EpisodeOne"
```

**Generate a Full Story (All Episodes):**

```bash
uv run scripts/run.py --story "MyStory" --run-all
```

#### 2. Advanced Configuration

| Argument            | Type   | Default   | Description                                                   |
| ------------------- | ------ | --------- | ------------------------------------------------------------- |
| `--story`           | `str`  | Required  | Name of the story folder.                                     |
| `--episode`         | `str`  | `Series1` | Name of the episode folder (optional if `--run-all` is used). |
| `--scenes`          | `int`  | `5`       | Number of scenes to generate per episode.                     |
| `--run-all`         | `flag` | `False`   | Trigger batch processing for all episodes in the story.       |
| `--genre`           | `str`  | `""`      | Genre of the story (e.g., Xuanhuan, Xiuxian, Sci-Fi).         |
| `--reference-story` | `str`  | `""`      | Reference story or style to imitate (e.g., Sword of Coming).  |

#### 3. Style & Genre Control

Control the content tone and style:

```bash
# Generate a "Xuanhuan" (Fantasy) style story referencing "Sword of Coming"
uv run scripts/run.py \
  --story "DragonTale" \
  --episode "01_Origin" \
  --genre "Xuanhuan" \
  --reference-story "Sword of Coming"

# Generate an entire story with consistent genre
uv run scripts/run.py \
  --story "DragonTale" \
  --run-all \
  --genre "Xuanhuan" \
  --reference-story "Sword of Coming"
```

## 🧪 Testing

The project includes a comprehensive test suite using pytest. Tests are located in the `test/` directory.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest test/test_script_analyzer.py

# Run tests with verbose output
uv run pytest -v

# Run tests with coverage report
uv run pytest --cov=magicplay
```

### Test Structure

```
test/
├── __init__.py
├── conftest.py              # Test configuration and fixtures
├── test_script_analyzer.py  # Tests for ScriptAnalyzer class
├── test_video_generator.py  # Tests for VideoGenerator class
├── test_story_consistency.py # Tests for StoryConsistencyManager class
├── test_image_service.py    # Tests for ImageService
├── test_video_api.py        # Tests for VideoAPI
├── test_llm_service.py      # Tests for LLMService
└── test_integration.py      # Integration tests
```

## 🔧 Development

### Key Architectural Patterns

1. **Orchestrator Pattern**: Central coordination of complex workflows
2. **Generator Pattern**: Specialized components for content creation
3. **Manager Pattern**: State and consistency management
4. **Service Pattern**: External API abstractions
5. **Three-Phase Optimization**: Progressive enhancement strategy

### Extending the System

#### Adding New Generators
```python
from magicplay.generators.base import BaseGenerator

class NewGenerator(BaseGenerator):
    def generate(self, context: dict) -> dict:
        # Implementation
        return {"output": "generated_content"}
```

#### Customizing Optimization Phases
```python
# In orchestrator.py
class Orchestrator:
    def __init__(self, ...):
        # Enable/disable optimization phases
        self.enable_phase1 = True  # Character consistency
        self.enable_phase2 = True  # Unified generation
        self.enable_phase3 = True  # Multi-frame
```

#### Adding New Analyzers
```python
from magicplay.analyzer.base import BaseAnalyzer

class NewAnalyzer(BaseAnalyzer):
    def analyze(self, content: str) -> AnalysisResult:
        # Custom analysis logic
        return AnalysisResult(...)
```

## 📈 Performance Considerations

### Memory Management
- Script memory is maintained between scenes for continuity
- Character images are cached and reused across episodes
- Scene concept images are generated once per scene

### API Usage Optimization
- Batch processing of episodes reduces API initialization overhead
- Character images are generated only once per story
- Scene concept images serve as references for multiple video generation attempts

### Quality vs. Speed Trade-offs
- **Phase 1**: One-time cost for character consistency (worth the investment)
- **Phase 2**: Minimal overhead (concept image + i2v generation)
- **Phase 3**: Additional processing for long scenes only (>8s)

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Implement your changes
4. Add tests for new functionality
5. Ensure all tests pass (`uv run pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style Guidelines
- Follow PEP 8 guidelines
- Use type hints extensively
- Write comprehensive docstrings
- Maintain modular architecture
- Add tests for new functionality

## 📚 API Reference

### Core Classes

#### `Orchestrator`
Main coordination class for single episode generation.

**Key Methods:**
- `run(initial_memory: str = "")`: Execute full episode generation
- `_ensure_character_images(story_context: str)`: Phase 1 implementation
- `_generate_single_video(...)`: Phase 2 fallback method

#### `StoryConsistencyManager`
Manages character consistency across scenes.

**Key Methods:**
- `load_from_story_bible(content: str)`: Parse story bible format
- `has_character_images() -> bool`: Check if character images exist
- `get_all_character_images() -> Dict[str, str]`: Get all character image paths

#### `SceneSegmentGenerator`
Implements Phase 3 multi-frame generation.

**Key Methods:**
- `generate_scene_segments(...)`: Generate segments for long scenes
- `analyze_scene_for_key_moments(...)`: Identify key moments in script
- `stitch_segments(...)`: Combine segments into final video

## 🚨 Troubleshooting

### Common Issues

1. **Character images not generating**
   - Check story bible format in `data/story/{StoryName}/story_bible.md`
   - Verify API key for image generation
   - Check `has_character_images()` logic in `StoryConsistencyManager`

2. **Video generation failures**
   - Verify Dashscope API key
   - Check concept image generation in Phase 2
   - Review script analysis for duration estimation

3. **Memory continuity issues**
   - Check `generated_scripts/` directory for script files
   - Verify memory parameter passing between scenes

### Debugging Tips

```bash
# Enable verbose logging
DEBUG=1 uv run scripts/run.py --story "MyStory" --episode "01_EpisodeOne"

# Test individual components
python -c "from magicplay.generators.character_gen import CharacterImageGenerator; gen = CharacterImageGenerator('TestStory'); print(gen.output_dir)"
```

## 🔮 Future Roadmap

### Planned Enhancements
- [ ] **Phase 4**: Audio generation and synchronization
- [ ] **Phase 5**: Multi-character interaction modeling
- [ ] **Phase 6**: Dynamic camera movement generation
- [ ] Enhanced prompt engineering templates
- [ ] Real-time generation preview
- [ ] Web interface for configuration

### Research Directions
- Advanced consistency models for character animation
- Cross-modal alignment (text-visual-audio)
- Adaptive story pacing algorithms
- Quality prediction models for AI-generated content

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- DeepSeek for LLM capabilities
- Aliyun Dashscope for video generation
- The open-source community for inspiration and tools

---

**MagicPlay**: Transforming stories into visual experiences, one frame at a time.