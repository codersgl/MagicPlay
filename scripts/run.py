# from magicplay.scene_generate.content import ScenesPromptGenerator
from magicplay.scene_generate.video import VideoGenerator


def main():
    print("Starting generation...")
    # scene_prompt_generator = ScenesPromptGenerator()
    # scene_prompt_generator.generate_scene()
    video_generator = VideoGenerator()
    video_generator.generate_video()
    print("Generation complete!")


if __name__ == "__main__":
    main()
