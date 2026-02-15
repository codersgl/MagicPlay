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
│   ├── core/               # Orchestration logic
│   ├── generators/         # Content & video generators
│   ├── prompts/            # Prompt templates
│   ├── services/           # External API services
│   └── utils/              # Utility modules
├── data/                   # Generated data (stories, scenes, scripts)
│   └── story/              # Story-specific data
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
uv run scripts/run.py --story "MyStory" --episode "01_EpisodeOne"
```

You can modify command line arguments to control generation:
```bash
# Run all episodes in a story
uv run scripts/run.py --story "MyStory" --run-all

# Generate specific number of scenes
uv run scripts/run.py --story "MyStory" --episode "01_EpisodeOne" --scenes 3
```

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
