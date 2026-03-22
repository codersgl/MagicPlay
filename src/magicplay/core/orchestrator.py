import math
from pathlib import Path
from typing import Optional, Tuple

from magicplay.analyzer.script_analyzer import ScriptAnalyzer
from magicplay.consistency.story_consistency import StoryConsistencyManager
from magicplay.generators.character_gen import CharacterImageGenerator
from magicplay.generators.scene_concept_gen import SceneConceptGenerator
from magicplay.generators.scene_segment_gen import SceneSegmentGenerator
from magicplay.generators.script_gen import (
    ScriptGenerator,
    extract_scene_exit_state,
    _extract_visual_key_from_script,
)
from magicplay.generators.video_gen import VideoGenerator
from magicplay.utils.media import MediaUtils
from magicplay.utils.paths import DataManager


class Orchestrator:
    def __init__(
        self,
        story_name: str,
        episode_name: str,
        max_scenes: int = 5,
        genre: str = "",
        reference_story: str = "",
    ):
        self.story_name = story_name
        self.episode_name = episode_name
        self.max_scenes = max_scenes
        self.genre = genre
        self.reference_story = reference_story

        DataManager.ensure_structure(story_name, episode_name)

        self.scenes_dir = DataManager.get_scenes_path(story_name, episode_name)
        self.scripts_dir = DataManager.get_generated_scripts_path(
            story_name, episode_name
        )
        self.videos_dir = DataManager.get_video_output_path(story_name, episode_name)

        # Initialize Generators
        # Prompts are loaded from default location src/magicplay/prompts unless specified
        self.script_gen = ScriptGenerator(
            output_dir=self.scripts_dir,
            genre=self.genre,
            reference_story=self.reference_story,
        )
        self.video_gen = VideoGenerator()
        self.scene_concept_gen = SceneConceptGenerator(story_name, episode_name)

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

        # If no story bible found, auto-generate one
        if not story_ctx or not story_ctx.strip():
            print(
                f"No story bible found for '{self.story_name}'. Auto-generating story bible..."
            )
            try:
                # Generate story idea from parameters
                story_idea = f"Story Title: {self.story_name}"
                if self.genre:
                    story_idea += f", Genre: {self.genre}"
                if self.reference_story:
                    story_idea += f", Reference Story: {self.reference_story}"

                story_ctx = self.script_gen.generate_story_outline(story_idea)

                # Ensure story directory exists
                story_path.mkdir(parents=True, exist_ok=True)

                # Save the generated story bible
                story_bible_path = story_path / "story_bible.md"
                story_bible_path.write_text(story_ctx, encoding="utf-8")
                print(f"Story bible auto-generated and saved to: {story_bible_path}")

            except Exception as e:
                print(f"Warning: Failed to auto-generate story bible: {e}")
                # Continue with empty story context

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

    def _ensure_character_images(self, story_context: str) -> None:
        """
        Ensure all characters have consistent images generated.
        This is Phase 1 of the optimization plan.
        """
        try:
            # Create consistency manager
            consistency_manager = StoryConsistencyManager(self.story_name)

            has_characters = False

            # If story context exists, load from it
            if story_context and story_context.strip():
                try:
                    print(
                        f"Loading story bible content (length: {len(story_context)} chars)..."
                    )
                    consistency_manager.load_from_story_bible(story_context)
                    print(
                        f"Successfully loaded {len(consistency_manager.characters)} characters from story bible"
                    )
                    if consistency_manager.characters:
                        print(
                            f"Characters found: {list(consistency_manager.characters.keys())}"
                        )
                        has_characters = True
                    else:
                        print(
                            "Warning: Story bible loaded but no characters were parsed"
                        )
                except Exception as e:
                    print(f"Warning: Failed to load story bible: {e}")
                    import traceback

                    traceback.print_exc()
            else:
                print("Warning: No story context found")

            # Check if we have any characters loaded
            if not has_characters:
                print(
                    "Note: No character information found in story context. Continuing without character images."
                )
                # Still check for existing character images
                from magicplay.utils.paths import DataManager

                anchors_dir = DataManager.get_character_anchors_path(self.story_name)
                if anchors_dir.exists():
                    existing_files = (
                        list(anchors_dir.glob("*.png"))
                        + list(anchors_dir.glob("*.jpg"))
                        + list(anchors_dir.glob("*.jpeg"))
                    )
                    if existing_files:
                        print(
                            f"Found {len(existing_files)} existing image files in character anchors directory"
                        )
                else:
                    print(f"Character anchors directory does not exist: {anchors_dir}")
                return

            # Check if any characters already have images associated
            character_images = consistency_manager.get_all_character_images()
            if character_images:
                print(
                    f"Found {len(character_images)} characters with existing image paths"
                )

            # Check character anchors directory for existing image files
            from magicplay.utils.paths import DataManager

            anchors_dir = DataManager.get_character_anchors_path(self.story_name)
            if anchors_dir.exists():
                existing_files = (
                    list(anchors_dir.glob("*.png"))
                    + list(anchors_dir.glob("*.jpg"))
                    + list(anchors_dir.glob("*.jpeg"))
                )
                if existing_files:
                    print(
                        f"Found {len(existing_files)} image files in character anchors directory"
                    )

                    # Try to load existing images and associate them with characters
                    loaded_images = consistency_manager.load_character_images_from_dir(
                        anchors_dir
                    )
                    if loaded_images:
                        print(
                            f"Associated {len(loaded_images)} existing images with characters: {list(loaded_images.keys())}"
                        )

            # Generate missing character images (ensure_character_images already handles missing ones)
            if consistency_manager.characters:
                print(
                    f"Ensuring images for {len(consistency_manager.characters)} characters..."
                )
                character_gen = CharacterImageGenerator(self.story_name)
                generated_images = character_gen.ensure_character_images(
                    consistency_manager
                )

                if generated_images:
                    print(
                        f"Successfully ensured character images: {list(generated_images.keys())}"
                    )
                else:
                    print(
                        "No character images were generated (may already exist or generation failed)."
                    )
            else:
                print("No characters found to generate images for.")

        except Exception as e:
            print(f"Warning: Failed to generate character images: {e}")
            import traceback

            traceback.print_exc()
            # Continue without character images

    def _generate_single_video(
        self,
        visual_prompt_text: str,
        video_path: Path,
        ref_img_path: Optional[str],
        duration: Optional[int],
    ) -> Path:
        """
        Generate a single video using the unified mode.
        This is the fallback method when multi-frame generation is not used or fails.
        """
        print(f"Generating video with unified mode...")
        # Force unified mode to ensure consistent image-to-video generation
        generated_video = self.video_gen.generate_video(
            visual_prompt_text,
            video_path,
            ref_img_path=ref_img_path,
            duration=duration,
            force_unified_mode=True,  # Enforce Phase 2 optimization
        )
        return generated_video

    def run(self, initial_memory: str = "") -> Tuple[Optional[Path], str]:
        try:
            story_ctx, episode_ctx = self.load_context()
        except Exception as e:
            print(f"Error loading context: {e}")
            return None, ""

        video_files = []
        memory = initial_memory

        print(
            f"Starting generation for episode: {self.episode_name} of Story: {self.story_name}"
        )

        # Generate character images if needed (Phase 1: Character Consistency Enhancement)
        self._ensure_character_images(story_ctx)

        # R2: Load character profiles ONCE before the scene loop (avoid repeated loading)
        character_profiles: dict = {}
        character_images: dict = {}
        visual_style_prompt: str = ""
        try:
            consistency_manager = StoryConsistencyManager(self.story_name)
            consistency_manager.load_from_story_bible(story_ctx)
            character_profiles = (
                consistency_manager.get_all_formatted_visual_tags() or {}
            )
            character_images = consistency_manager.get_all_character_images() or {}

            # Extract visual style from consistency manager to enforce uniform style across scenes
            if consistency_manager.visual_style:
                vs = consistency_manager.visual_style
                visual_style_prompt = (
                    f"- Camera & Cinematic Style: {vs.cinematic_style}\n"
                    f"- Ambient Mood: {vs.mood}\n"
                    f"- Color Palette: {', '.join(vs.color_palette)}\n"
                    f"- Lighting: {vs.lighting_style}"
                )
                print("Loaded global visual style for consistency.")

            if character_profiles:
                print(
                    f"Loaded {len(character_profiles)} character profiles for Visual Tags anchoring"
                )
        except Exception as e:
            print(f"Warning: Failed to load character profiles/style: {e}")

        # Determine scenes to process
        # Check if there are pre-defined scene prompts in data directory
        scene_prompts = DataManager.get_scenes_prompts(
            self.story_name, self.episode_name
        )

        # [NEW]: Pre-process outline into scenes if no physical scene files exist
        if not scene_prompts and episode_ctx:
            print(
                "No scene definitions found, but episode outline exists. Splitting outline into scenes..."
            )
            try:
                extracted_scenes = self.script_gen.split_outline_into_scenes(
                    episode_ctx
                )
                if extracted_scenes:
                    scenes_dir = DataManager.get_scenes_path(
                        self.story_name, self.episode_name
                    )
                    scenes_dir.mkdir(parents=True, exist_ok=True)

                    for i, scene_content in enumerate(extracted_scenes):
                        scene_file_name = f"scene_{i + 1}.md"
                        scene_file_path = scenes_dir / scene_file_name
                        scene_file_path.write_text(scene_content, encoding="utf-8")

                    # Refresh scene_prompts after generating them
                    scene_prompts = DataManager.get_scenes_prompts(
                        self.story_name, self.episode_name
                    )
                    print(
                        f"Successfully generated {len(scene_prompts)} scene files from outline."
                    )
            except Exception as e:
                print(f"Warning: Failed to split outline into scenes: {e}")

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

        # Track previous video, previous concept image, and previous visual key for continuity
        previous_video_path = None
        previous_concept_image_path = None
        previous_visual_key = None

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

            # B4: Track whether script was generated in this run for physics check
            script_was_generated = False

            # If script doesn't exist, generate it
            if not script_path.exists():
                print(f"Generating script for {scene_name}...")

                generated_script_path = self.script_gen.generate_scene_script(
                    scene_name=scene_name,
                    story_context=story_ctx,
                    episode_context=episode_ctx,
                    memory=memory,
                    scene_prompt=scene_prompt_content,
                    character_profiles=character_profiles,
                )
                # Ensure the path matches what we expect
                if generated_script_path != script_path:
                    print(
                        f"Warning: Generated script path mismatch. Expected {script_path}, got {generated_script_path}"
                    )
                    script_path = generated_script_path
                script_was_generated = True
            else:
                print(f"Script already exists: {script_path}")

            # Update memory for next iteration
            # Build structured exit-state summary + full script for reliable continuity
            if script_path.exists():
                full_script = script_path.read_text(encoding="utf-8")
                exit_state = extract_scene_exit_state(full_script)
                memory = f"## 前场状态交接\n{exit_state}\n\n---\n\n## 完整前场脚本\n{full_script}"

                # Update previous_visual_key for next scene's continuity
                previous_visual_key = _extract_visual_key_from_script(full_script)

                # B4: Physics check only for scripts generated in this run
                if script_was_generated:
                    try:
                        from magicplay.analyzer.physics_checker import PhysicsChecker

                        physics_checker = PhysicsChecker()
                        violations = physics_checker.analyze(script_path)
                        if violations:
                            print(
                                f"⚠️ Physics checker found {len(violations)} potential issue(s) in {scene_name}"
                            )
                            for v in violations[:3]:  # Show first 3
                                print(f"  - Line {v.line_number}: {v.description}")
                            if len(violations) > 3:
                                print(f"  ... and {len(violations) - 3} more")
                        else:
                            print(f"✓ Physics check passed for {scene_name}")
                    except Exception as e:
                        print(f"Note: Physics check skipped: {e}")

            # 1.2 Video Generation with Unified Mode (Phase 2 Optimization)
            video_path = self.videos_dir / f"{scene_name}.mp4"
            if not video_path.exists():
                print(f"Generating visual prompt for video...")
                try:
                    # R1: Extract/generate visual prompt using character profiles
                    visual_prompt_text = self.script_gen.generate_visual_prompt(
                        script_path,
                        character_profiles=character_profiles
                        if character_profiles
                        else None,
                        visual_style=visual_style_prompt,
                        previous_visual_key=previous_visual_key,
                    )

                    # Phase 2: Generate scene concept image (first frame)
                    scene_concept_image = None
                    try:
                        # Generate or get concept image for this scene
                        scene_concept_image = (
                            self.scene_concept_gen.ensure_scene_concept_image(
                                scene_name=scene_name,
                                scene_script=script_path.read_text(encoding="utf-8"),
                                use_previous_scene=previous_concept_image_path
                                is not None,
                                previous_scene_image=(
                                    str(previous_concept_image_path)
                                    if previous_concept_image_path
                                    else None
                                ),
                                story_context=story_ctx,
                                character_images=character_images,
                                character_profiles=character_profiles
                                if character_profiles
                                else None,
                                visual_style=visual_style_prompt,
                            )
                        )

                        if scene_concept_image:
                            print(
                                f"Scene concept image generated: {scene_concept_image}"
                            )
                        else:
                            print(
                                f"Warning: Failed to generate scene concept image for {scene_name}"
                            )
                    except Exception as e:
                        print(f"Warning: Scene concept generation failed: {e}")
                        # Continue without concept image

                    # Use scene concept image as reference for video generation
                    ref_img_path = None
                    if scene_concept_image and Path(scene_concept_image).exists():
                        # Use the generated concept image as reference
                        ref_img_path = scene_concept_image
                        previous_concept_image_path = Path(scene_concept_image)
                        print(f"Using scene concept image as reference: {ref_img_path}")
                    elif previous_video_path and Path(previous_video_path).exists():
                        # Fallback to previous video's last frame (legacy behavior)
                        last_frame_path = (
                            self.videos_dir
                            / f"last_frame_{Path(previous_video_path).stem}.jpg"
                        )
                        if MediaUtils.extract_last_frame(
                            previous_video_path, last_frame_path
                        ):
                            ref_img_path = str(last_frame_path)
                            print(
                                f"Using previous video's last frame as reference: {ref_img_path}"
                            )

                    # Analyze script to determine optimal video duration
                    print(f"Analyzing script for optimal duration...")
                    script_analyzer = ScriptAnalyzer()
                    analysis_result = script_analyzer.analyze_file(str(script_path))

                    estimated_duration = None
                    if analysis_result:
                        estimated_duration = analysis_result.estimated_duration
                        print(
                            f"Script analysis: scene_type={analysis_result.scene_type.value}, "
                            f"words={analysis_result.total_words}, "
                            f"estimated_duration={estimated_duration}s, "
                            f"complexity={analysis_result.complexity_score:.2f}"
                        )

                    # R4: Clamp duration to Wan2.6 supported values (5s or 10s).
                    # Use 10s for scenes estimated at 8s or more, otherwise 5s.
                    if estimated_duration and estimated_duration >= 8:
                        duration = 10
                    else:
                        duration = 5

                    # Phase 3: Multi-frame generation for scenes estimated over 10s
                    use_multi_frame = True  # Enable multi-frame generation

                    if (
                        use_multi_frame
                        and estimated_duration
                        and estimated_duration > 10
                    ):
                        # For longer scenes, try multi-frame generation
                        print(
                            f"Using multi-frame generation for {scene_name} (total duration: {estimated_duration}s, split into {math.ceil(estimated_duration / 10)} segments)..."
                        )
                        try:
                            scene_segment_gen = SceneSegmentGenerator(
                                self.story_name, self.episode_name
                            )

                            # Generate scene segments using multi-frame approach
                            segments = scene_segment_gen.generate_scene_segments(
                                scene_name=scene_name,
                                scene_script=script_path.read_text(encoding="utf-8"),
                                base_visual_prompt=visual_prompt_text,
                                segment_duration=estimated_duration,
                                use_multi_frame=True,
                            )

                            if segments and len(segments) > 1:
                                # Stitch segments together
                                stitched_video_path = scene_segment_gen.stitch_segments(
                                    scene_name, segments
                                )
                                if (
                                    stitched_video_path
                                    and Path(stitched_video_path).exists()
                                ):
                                    video_path = Path(stitched_video_path)
                                    print(
                                        f"Multi-frame generation successful: {video_path}"
                                    )
                                else:
                                    print(
                                        f"Multi-frame stitching failed, falling back to single segment"
                                    )
                                    # Fallback to single video generation
                                    video_path = self._generate_single_video(
                                        visual_prompt_text,
                                        video_path,
                                        ref_img_path,
                                        duration,
                                    )
                            else:
                                print(
                                    f"Multi-frame generation returned {len(segments) if segments else 0} segments, falling back to single segment"
                                )
                                # Fallback to single video generation
                                video_path = self._generate_single_video(
                                    visual_prompt_text,
                                    video_path,
                                    ref_img_path,
                                    duration,
                                )
                        except Exception as e:
                            print(
                                f"Multi-frame generation failed for {scene_name}: {e}"
                            )
                            print("Falling back to single segment generation")
                            # Fallback to single video generation
                            video_path = self._generate_single_video(
                                visual_prompt_text, video_path, ref_img_path, duration
                            )
                    else:
                        # Use single-frame generation
                        print(f"Using single-frame generation for {scene_name}...")
                        video_path = self._generate_single_video(
                            visual_prompt_text, video_path, ref_img_path, duration
                        )

                    if video_path and video_path.exists():
                        video_files.append(str(video_path))
                        previous_video_path = video_path

                except Exception as e:
                    print(f"Failed to generate video for {scene_name}: {e}")
                    # Continue gracefully
            else:
                print(f"Video already exists: {video_path}")
                video_files.append(str(video_path))
                previous_video_path = video_path

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
    def __init__(self, story_name: str, genre: str = "", reference_story: str = ""):
        self.story_name = story_name
        self.genre = genre
        self.reference_story = reference_story
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

            try:
                orchestrator = Orchestrator(
                    story_name=self.story_name,
                    episode_name=episode_name,
                    genre=self.genre,
                    reference_story=self.reference_story,
                )
                final_video, memory = orchestrator.run(initial_memory=memory)

                if final_video and final_video.exists():
                    episode_videos.append(str(final_video))
            except Exception as e:
                print(f"Error processing episode {episode_name}: {e}")
                # Continue with next episode

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
