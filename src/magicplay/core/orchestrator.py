from typing import List, Tuple
from pathlib import Path

from magicplay.generators.script_gen import ScriptGenerator
from magicplay.generators.video_gen import VideoGenerator
from magicplay.utils.paths import DataManager
from magicplay.utils.media import MediaUtils


class Orchestrator:
    def __init__(self, story_name: str, episode_name: str, max_scenes: int = 5):
        self.story_name = story_name
        self.episode_name = episode_name
        self.max_scenes = max_scenes

        DataManager.ensure_structure(story_name, episode_name)

        self.scenes_dir = DataManager.get_scenes_path(story_name, episode_name)
        self.scripts_dir = DataManager.get_generated_scripts_path(
            story_name, episode_name
        )
        self.videos_dir = DataManager.get_video_output_path(story_name, episode_name)

        # Initialize Generators
        # Prompts are loaded from default location src/magicplay/prompts unless specified
        self.script_gen = ScriptGenerator(output_dir=self.scripts_dir)
        self.video_gen = VideoGenerator()

    def load_context(self) -> Tuple[str, str]:
        # Allow checking both folder/name.md and folder/name_outline.md
        story_path = DataManager.get_story_path(self.story_name)
        episode_path = DataManager.get_episode_path(self.story_name, self.episode_name)

        story_ctx = ""
        # Try to find any md file in story dir to use as context if specific one doesn't exist
        if story_path.exists():
            md_files = list(story_path.glob("*.md"))
            if md_files:
                story_ctx = md_files[0].read_text(encoding="utf-8")

        episode_ctx = ""
        if episode_path.exists():
            # Look for explicit outline files or just the first md file
            # Exclude files in subdirectories by not using rglob, but glob is non-recursive by default.
            # However, we should be careful not to pick up randomness if possible.
            md_files = list(episode_path.glob("*.md"))
            if md_files:
                episode_ctx = md_files[0].read_text(encoding="utf-8")
            elif story_ctx:
                # [Auto-Generate Feature]
                # If no episode outline exists but we have a story bible, generate the outline automatically.
                print(
                    f"No episode outline found for {self.episode_name}. Generating one from Story Bible..."
                )
                try:
                    episode_idea = f"Episode Name: {self.episode_name}"
                    episode_ctx = self.script_gen.generate_episode_outline(
                        story_ctx, episode_idea
                    )

                    # Save the generated outline
                    outline_path = episode_path / f"{self.episode_name}_outline.md"
                    outline_path.write_text(episode_ctx, encoding="utf-8")
                    print(f"Episode outline generated and saved to: {outline_path}")
                except Exception as e:
                    print(f"Warning: Failed to auto-generate episode outline: {e}")

        return story_ctx, episode_ctx

    def run(self, initial_memory: str = "") -> Tuple[Path | None, str]:
        story_ctx, episode_ctx = self.load_context()
        video_files = []
        memory = initial_memory

        print(
            f"Starting generation for episode: {self.episode_name} of Story: {self.story_name}"
        )

        # Determine scenes to process
        # Check if there are pre-defined scene prompts in data directory
        scene_prompts = DataManager.get_scenes_prompts(
            self.story_name, self.episode_name
        )

        if scene_prompts:
            print(f"Found {len(scene_prompts)} scene definitions in data directory.")
            scenes_to_process = []
            for prompt_file in scene_prompts:
                # Extract scene name from filename (remove extension)
                scene_name = prompt_file.stem
                scenes_to_process.append((scene_name, prompt_file))
        else:
            print(
                f"No scene definitions found. Generating {self.max_scenes} sequential scenes."
            )
            scenes_to_process = [
                (f"scene_{i}", None) for i in range(1, self.max_scenes + 1)
            ]

        # 1. Loop through scenes
        for scene_name, prompt_file in scenes_to_process:
            print(f"\n--- Processing {scene_name} ---")

            # 1.1 Script Generation
            # If prompt file exists, use its content as prompt
            scene_prompt_content = ""
            if prompt_file:
                scene_prompt_content = prompt_file.read_text(encoding="utf-8")

            # Script will be saved to generated_scripts directory
            script_path = self.scripts_dir / f"{scene_name}.md"

            # If script doesn't exist, generate it
            if not script_path.exists():
                print(f"Generating script for {scene_name}...")
                generated_script_path = self.script_gen.generate_scene_script(
                    scene_name=scene_name,
                    story_context=story_ctx,
                    episode_context=episode_ctx,
                    memory=memory,
                    scene_prompt=scene_prompt_content,
                )
                # Ensure the path matches what we expect
                if generated_script_path != script_path:
                    print(
                        f"Warning: Generated script path mismatch. Expected {script_path}, got {generated_script_path}"
                    )
                    script_path = generated_script_path
            else:
                print(f"Script already exists: {script_path}")

            # Update memory for next iteration
            if script_path.exists():
                memory = script_path.read_text(encoding="utf-8")

            # 1.2 Video Generation (from Visual Prompt)
            video_path = self.videos_dir / f"{scene_name}.mp4"
            if not video_path.exists():
                print(f"Generating visual prompt for video...")
                try:
                    # Summarize script into visual prompt
                    visual_prompt_text = self.script_gen.generate_visual_prompt(
                        script_path
                    )

                    print(f"Generating video...")
                    video_path = self.video_gen.generate_video(
                        visual_prompt_text, video_path
                    )

                    if video_path and video_path.exists():
                        video_files.append(str(video_path))

                except Exception as e:
                    print(f"Failed to generate video for {scene_name}: {e}")
                    # Continue gracefully
            else:
                print(f"Video already exists: {video_path}")
                video_files.append(str(video_path))

        # 2. Stitch Videos
        if video_files:
            output_file = self.videos_dir / f"{self.episode_name}_full.mp4"
            try:
                MediaUtils.stitch_videos(video_files, output_file)

                if output_file.exists():
                    print(f"Episode complete: {output_file}")
                    return output_file, memory
                else:
                    print(
                        f"Episode scripts/video generated, but full video missing (stitching skipped/failed)."
                    )
                    return None, memory

            except Exception as e:
                print(f"Stitching failed: {e}")
                return None, memory
        else:
            print("No videos generated to stitch.")
            return None, memory


class StoryOrchestrator:
    def __init__(self, story_name: str):
        self.story_name = story_name
        self.story_path = DataManager.get_story_path(story_name)

    def run(self):
        print(f"Starting Story Generation: {self.story_name}")

        episodes = DataManager.get_episodes(self.story_name)
        if not episodes:
            print("No episodes found.")
            return

        episode_videos = []
        memory = ""

        for ep_path in episodes:
            episode_name = ep_path.name
            print(f"\n=== Processing Episode: {episode_name} ===")

            orchestrator = Orchestrator(
                story_name=self.story_name, episode_name=episode_name
            )
            final_video, memory = orchestrator.run(initial_memory=memory)

            if final_video and final_video.exists():
                episode_videos.append(str(final_video))

        # Stitch all episodes into a movie
        if len(episode_videos) > 0:
            final_story_video = (
                DataManager.VIDEOS_DIR
                / self.story_name
                / f"{self.story_name}_full_movie.mp4"
            )
            try:
                print(f"Stitching full story movie...")
                MediaUtils.stitch_videos(episode_videos, final_story_video)
                print(f"Story complete! Movie saved to: {final_story_video}")
            except Exception as e:
                print(f"Failed to stitch story: {e}")
        else:
            print("Not enough episodes generated to stitch story.")
