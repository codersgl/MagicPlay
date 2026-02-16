# MagicPlay

MagicPlay is an automated content generation tool that creates short play scripts and accompanying videos using advanced AI models.

## Showcase

https://github.com/user-attachments/assets/ad2bcb82-cfe9-42ed-9d62-32d4830128f9

## Features

- **Scene Generation**: Generates creative short play scripts using LLMs (focusing on DeepSeek).
- **Video Generation**: Creates video content based on generated scenes using Aliyun Dashscope (Wan2.6-t2v model).

## Project Structure

The project separates source code from generated data:

```
MagicPlay/
├── src/magicplay/          # Source code
│   ├── core/               # Orchestration logic (Orchestrator)
│   ├── generators/         # Content & video generators (ScriptGenerator, VideoGenerator)
│   ├── prompts/            # Prompt templates
│   ├── services/           # External API services (LLM, Video API)
│   └── utils/              # Utility modules (Paths, Media)
├── data/                   # Generated data
│   └── story/              # Story-specific data ({StoryName}/{EpisodeName}/generated_scripts/)
├── videos/                 # Generated videos ({StoryName}/{EpisodeName}/)
└── scripts/
    └── run.py              # Entry point script
```

## Prerequisites

- **Python**: Managed via `uv`.
- **API Keys**: You need the following environment variables set (can be loaded via a `.env` file):
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
Generates scripts and videos for a specific episode within a story.
```bash
uv run scripts/run.py --story "MyStory" --episode "01_EpisodeOne"
```

**Generate a Full Story:**
Sequentially runs generation for all defined episodes in a story structure.
```bash
uv run scripts/run.py --story "MyStory" --run-all
```

#### 2. Advanced Configuration

You can customize the generation process using additional flags:

| Argument    | Type   | Default   | Description                                                       |
| ----------- | ------ | --------- | ----------------------------------------------------------------- |
| `--story`   | `str`  | Required  | Name of the story folder.                                         |
| `--episode` | `str`  | `Series1` | Name of the episode folder (required unless `--run-all` is used). |
| `--scenes`  | `int`  | `5`       | Number of scenes to generate per episode.                         |
| `--run-all` | `flag` | `False`   | Trigger batch processing for all episodes in the story.           |

#### 3. Style & Genre Control

Control the content tone and style using these parameters:

```bash
# Generate a "Xuanhuan" (Fantasy) style story referencing "Sword of Coming"
uv run scripts/run.py \
  --story "DragonTale" \
  --episode "01_Origin" \
  --genre "Xuanhuan" \
  --reference-story "Sword of Coming"
```

- **`--genre`**: Specifies the genre (e.g., "Xuanhuan", "Sci-Fi", "Romance").
- **`--reference-story`**: Provides a stylistic reference or specific narrative tone to imitate.

## Architecture & Workflow

1.  **Input**: Prompts are loaded from `src/magicplay/prompts/` (e.g., `gen_episode.md`).
2.  **Processing**:
    - `ScriptGenerator` interacts with the LLM to create intermediate Markdown scripts.
    - `Orchestrator` manages the flow between script generation and video production.
3.  **Output**:
    - Scripts are saved to `data/story/{StoryName}/{EpisodeName}/generated_scripts/`.
    - Videos are saved to `videos/{StoryName}/{EpisodeName}/`.

## Development

- **Package Name**: `magicplay`
- **Path Management**: Uses `magicplay.utils.paths.DataManager`.
- **Code Style**: Follows PEP 8 guidelines and uses type hinting.
