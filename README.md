# MagicPlay

MagicPlay is an automated content generation tool that creates short play scripts and accompanying videos using advanced AI models.

## Features

- **Scene Generation**: Generates creative short play scripts using LLMs (focusing on DeepSeek).
- **Video Generation**: Creates video content based on generated scenes using Aliyun Dashscope (Wan2.6-t2v model).

## Project Structure

The project separates source code from generated data:

```
MagicPlay/
├── src/magicplay/          # Source code
│   ├── prompts/            # Input prompts for scene generation
│   ├── scene_generate/     # Core logic for content & video generation
│   └── utils.py            # Utility functions
├── data/
│   └── scenes/             # Generated scene scripts (Markdown)
├── videos/                 # Generated videos
└── scripts/
    └── run.py              # Entry point script
```

## Prerequisites

- **Python**: Managed via `uv`.
- **API Keys**: You need the following environment variables set:
  - `DEEPSEEK_API_KEY`: For script generation.
  - `DASHSCOPE_API_KEY`: For video generation.

## Installation

This project uses `uv` for dependency management.

```bash
uv sync
```

## Usage

To run the generation pipeline:

```bash
uv run scripts/run.py
```

You can modify `scripts/run.py` to toggle between generating scenes or videos:

```python
def main():
    # Uncomment to generate a new scene script
    # scene_prompt_generator = ScenesPromptGenerator()
    # scene_prompt_generator.generate_scene()
    
    # Generate video from existing scenes
    video_generator = VideoGenerator()
    video_generator.generate_video()
```

## Configuration

- **Prompts**: Add or modify prompt templates in `src/magicplay/prompts/`.
- **Scene Output**: Generated scripts are saved to `data/scenes/`.
- **Video Output**: Generated videos are saved to `videos/`.
