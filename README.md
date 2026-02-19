# MagicPlay

MagicPlay is an automated content generation tool that creates short play scripts and accompanying videos using advanced AI models.

## Showcase

<https://github.com/user-attachments/assets/ad2bcb82-cfe9-42ed-9d62-32d4830128f9>

## Features

- **Story Generation**: Generate complete story outlines with multiple episodes using LLMs (DeepSeek).
- **Scene Generation**: Creates creative short play scripts with detailed scene descriptions.
- **Video Generation**: Produces video content based on generated scenes using Aliyun Dashscope (Wan2.6-t2v model).
- **Batch Processing**: Run all episodes in a story sequentially with a single command.

## Project Structure

The project separates source code from generated data:

```
MagicPlay/
├── src/magicplay/          # Source code
│   ├── core/               # Orchestration logic (Orchestrator, StoryOrchestrator)
│   ├── generators/         # Content & video generators (ScriptGenerator, VideoGenerator)
│   ├── prompts/            # Prompt templates (gen_story.md, gen_episode.md, gen_scene.md)
│   ├── services/           # External API services (LLM, Video API)
│   └── utils/              # Utility modules (Paths, Media)
├── data/                   # Generated data
│   └── story/              # Story-specific data ({StoryName}/{EpisodeName}/generated_scripts/)
├── videos/                 # Generated videos ({StoryName}/{EpisodeName}/)
└── scripts/
    └── run.py              # Entry point script
```

## Prerequisites

- **Python**: >= 3.13 (managed via `uv`)
- **API Keys**: Set the following environment variables (can be loaded via a `.env` file):
  - `DEEPSEEK_API_KEY`: For script generation (via OpenAI client).
  - `DASHSCOPE_API_KEY`: For video generation (via Aliyun Dashscope).

## Installation

This project uses `uv` for dependency management.

```bash
uv sync
```

## Usage

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

## Architecture & Workflow

1. **Input**: Prompts are loaded from `src/magicplay/prompts/`:
    - `gen_story.md` - For generating overall story structure
    - `gen_episode.md` - For generating episode outlines
    - `gen_scene.md` - For generating detailed scene scripts
2. **Processing**:
    - `ScriptGenerator` interacts with the LLM to create intermediate Markdown scripts.
    - `Orchestrator` manages single episode generation flow.
    - `StoryOrchestrator` handles batch processing of all episodes in a story.
3. **Output**:
    - Scripts are saved to `data/story/{StoryName}/{EpisodeName}/generated_scripts/`.
    - Videos are saved to `videos/{StoryName}/{EpisodeName}/`.

## Development

- **Package Name**: `magicplay`
- **Path Management**: Uses `magicplay.utils.paths.DataManager`
- **Code Style**: Follows PEP 8 guidelines and uses type hinting

> [!NOTE]
>
> The project is not perfect. Feel free to fork it and open a PR.
