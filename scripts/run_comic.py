#!/usr/bin/env python3
"""
CLI entry point for comic generation.

Usage:
    python scripts/run_comic.py --story "MyStory" --episode "01" --style anime
    python scripts/run_comic.py --story "MyStory" --run-all
"""

import argparse
from pathlib import Path

from magicplay.core.comic_orchestrator import ComicOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Generate AI comic from story")
    parser.add_argument("--story", required=True, help="Story name")
    parser.add_argument("--episode", default="Series1", help="Episode name")
    parser.add_argument("--scenes", type=int, default=5, help="Number of scenes")
    parser.add_argument("--genre", default="", help="Genre (e.g., Xuanhuan, Sci-Fi)")
    parser.add_argument(
        "--reference-story", default="", help="Reference story for style"
    )
    parser.add_argument(
        "--style",
        default="anime",
        choices=["anime", "comic", "webtoon", "ink"],
        help="Comic art style",
    )
    parser.add_argument("--run-all", action="store_true", help="Process all episodes")

    args = parser.parse_args()

    # Get episodes
    if args.run_all:
        from magicplay.utils.paths import DataManager

        episodes = DataManager.get_episodes(args.story)
        episode_names = [ep.name for ep in episodes]
    else:
        episode_names = [args.episode]

    # Process each episode
    for episode_name in episode_names:
        print(f"\n{'='*60}")
        print(f"Generating comic: {args.story} / {episode_name}")
        print(f"{'='*60}\n")

        orchestrator = ComicOrchestrator(
            story_name=args.story,
            episode_name=episode_name,
            max_scenes=args.scenes,
            genre=args.genre,
            reference_story=args.reference_story,
            comic_style=args.style,
        )

        try:
            results = orchestrator.run()
            total_panels = sum(len(scene_results) for scene_results in results)
            print(f"\n✓ Comic generation complete!")
            print(f"  - Scenes: {len(results)}")
            print(f"  - Total panels: {total_panels}")
            print(f"  - Output: data/story/{args.story}/{episode_name}/panels/")
        except Exception as e:
            print(f"\n✗ Comic generation failed: {e}")
            raise


if __name__ == "__main__":
    main()
