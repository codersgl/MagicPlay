from pathlib import Path


class DataManager:
    """Helper class to manage data paths for Story -> episode -> Scenes hierarchy."""

    # src/magicplay/utils/paths.py -> utils -> magicplay -> src -> MagicPlay
    ROOT_DIR = Path(__file__).parents[3]
    DATA_DIR = ROOT_DIR / "data"
    VIDEOS_DIR = ROOT_DIR / "videos"

    @classmethod
    def get_story_path(cls, story_name: str) -> Path:
        return cls.DATA_DIR / "story" / story_name

    @classmethod
    def get_episode_path(cls, story_name: str, episode_name: str) -> Path:
        return cls.get_story_path(story_name) / episode_name

    @classmethod
    def get_scenes_path(cls, story_name: str, episode_name: str) -> Path:
        return cls.get_episode_path(story_name, episode_name) / "scenes"

    @classmethod
    def get_video_output_path(cls, story_name: str, episode_name: str) -> Path:
        """Returns the directory where videos for a specific episode should be saved."""
        return cls.VIDEOS_DIR / story_name / episode_name

    @classmethod
    def get_generated_scripts_path(cls, story_name: str, episode_name: str) -> Path:
        """Returns the directory where generated scripts should be saved."""
        return cls.get_episode_path(story_name, episode_name) / "generated_scripts"

    @classmethod
    def get_character_anchors_path(cls, story_name: str) -> Path:
        """Returns the directory where character anchor images should be saved."""
        return cls.get_story_path(story_name) / "character_anchors"

    @classmethod
    def get_scene_concepts_path(cls, story_name: str, episode_name: str) -> Path:
        """Returns the directory where scene concept images should be saved."""
        return cls.get_episode_path(story_name, episode_name) / "scene_concepts"

    @classmethod
    def ensure_structure(cls, story_name: str, episode_name: str):
        """Creates necessary directories for scenes and output videos."""
        cls.get_scenes_path(story_name, episode_name).mkdir(parents=True, exist_ok=True)
        cls.get_generated_scripts_path(story_name, episode_name).mkdir(
            parents=True, exist_ok=True
        )
        cls.get_video_output_path(story_name, episode_name).mkdir(
            parents=True, exist_ok=True
        )
        cls.get_character_anchors_path(story_name).mkdir(parents=True, exist_ok=True)
        cls.get_scene_concepts_path(story_name, episode_name).mkdir(
            parents=True, exist_ok=True
        )

    @classmethod
    def get_stories(cls) -> list[Path]:
        """Returns a list of story directories in the data directory, sorted."""
        if not cls.DATA_DIR.exists():
            return []

        # Only directories are considered stories
        stories = [p for p in cls.DATA_DIR.iterdir() if p.is_dir()]
        return sorted(stories, key=lambda p: p.name)

    @classmethod
    def get_episodes(cls, story_name: str) -> list[Path]:
        """Returns a list of episode directories for a given story, sorted."""
        story_path = cls.get_story_path(story_name)
        if not story_path.exists():
            return []

        # Only directories are considered episodes
        episodes = [
            p for p in story_path.iterdir() if p.is_dir() and p.name != "scenes"
        ]
        return sorted(episodes, key=lambda p: p.name)

    @classmethod
    def get_scenes_prompts(cls, story_name: str, episode_name: str) -> list[Path]:
        """Returns a list of scene prompt files (.md) for a given episode, sorted."""
        scenes_dir = cls.get_scenes_path(story_name, episode_name)
        if not scenes_dir.exists():
            return []

        # Look for .md files in the scenes directory
        scenes = list(scenes_dir.glob("*.md"))
        return sorted(scenes, key=lambda p: p.name)

    @staticmethod
    def read_prompt_file(source: str | Path) -> str:
        path = Path(source)
        file_to_read: Path | None = None

        if path.exists() and path.is_file():
            file_to_read = path
        elif path.exists() and path.is_dir():
            match = sorted(list(path.rglob("*.md")))
            if not match:
                raise FileNotFoundError(f"No .md files found in {path}")
            file_to_read = match[0]
        else:
            raise FileNotFoundError(f"Path not found: {path}")

        try:
            with open(file_to_read, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read prompt file {file_to_read}: {e}")
