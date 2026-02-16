import argparse
from magicplay.core.orchestrator import Orchestrator, StoryOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Generate MagicPlay episode")
    parser.add_argument("--story", type=str, required=True, help="Name of the story")
    parser.add_argument(
        "--episode", type=str, help="Name of the episode (optional if run-all is set)"
    )
    # Maintain backward compatibility
    parser.add_argument("--series", type=str, help="Alias for episode")

    parser.add_argument(
        "--scenes",
        type=int,
        default=5,
        help="Number of scenes to generate (if not using pre-defined scripts)",
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="Run all episodes in the story sequentially",
    )

    args = parser.parse_args()

    episode_name = args.episode or args.series or "Series1"

    if args.run_all:
        print(f"Starting FULL STORY generation for: {args.story}")
        orchestrator = StoryOrchestrator(args.story)
        orchestrator.run()
    else:
        print(
            f"Starting SINGLE EPISODE generation for Story: {args.story}, Episode: {episode_name}"
        )
        orchestrator = Orchestrator(args.story, episode_name, max_scenes=args.scenes)
        orchestrator.run()

    print("Generation complete!")


if __name__ == "__main__":
    main()
