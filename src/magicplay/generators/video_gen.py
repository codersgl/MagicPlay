from pathlib import Path
from typing import Optional, Tuple, Union

from magicplay.services.video_api import VideoService
from magicplay.utils.media import MediaUtils


class VideoGenerator:
    def __init__(
        self,
        api_provider: str = "qwen",
        size: Tuple[int, int] = (1280, 720),
        duration: int = 15,
        unified_mode: bool = True,  # Phase 2: Unified video generation mode
    ) -> None:
        self.service = VideoService(api_provider=api_provider)
        self.size = size
        self.duration = duration
        self.unified_mode = unified_mode

    def generate_video(
        self,
        visual_prompt: str,
        output_path: Union[str, Path],
        ref_img_path: Optional[Union[str, Path]] = None,
        duration: Optional[int] = None,
        force_unified_mode: Optional[bool] = None,
    ) -> Path:
        """
        Generate a video from a visual prompt string.

        Phase 2: Unified video generation mode:
        - Always use image-to-video (i2v) model when a reference image is provided
        - Even for first scene, generate concept image first, then use i2v
        - This ensures consistency across all video generation
        """
        output_path = Path(output_path)
        ref_path_obj = Path(ref_img_path) if ref_img_path else None

        # Determine if we should use unified mode
        use_unified = (
            force_unified_mode if force_unified_mode is not None else self.unified_mode
        )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Generating video to {output_path}...")

        # Unified mode logic
        if use_unified:
            if ref_path_obj:
                print(
                    f"Unified mode: Using reference image for image-to-video generation: {ref_path_obj}"
                )
            else:
                print(
                    f"Unified mode: No reference image provided. "
                    f"This is expected for the first scene - concept image should be generated separately."
                )
        else:
            if ref_path_obj:
                print(f"Legacy mode: Using reference image: {ref_path_obj}")

        # Use provided duration or fallback to instance default
        video_duration = duration if duration is not None else self.duration
        print(f"Video duration: {video_duration} seconds")

        try:
            # In unified mode, we always use the ref_img_path parameter if provided
            # The VideoService will use i2v model when ref_img_path is provided
            video_url = self.service.generate_video_url(
                prompt=visual_prompt,
                size=self.size,
                duration=video_duration,
                ref_img_path=str(ref_path_obj) if ref_path_obj else None,
            )

            if MediaUtils.download_video(video_url, output_path):
                print(f"Video saved to: {output_path}")
                return output_path
            else:
                raise RuntimeError("Failed to download generated video")

        except Exception as e:
            raise RuntimeError(f"Video generation failed: {e}")

    def generate_video_unified(
        self,
        visual_prompt: str,
        output_path: Union[str, Path],
        concept_image_path: Union[str, Path],
        duration: Optional[int] = None,
    ) -> Path:
        """
        Unified video generation method that explicitly requires a concept image.
        This is the recommended method for Phase 2 optimization.

        Args:
            visual_prompt: Visual prompt for the scene
            output_path: Path to save the generated video
            concept_image_path: Path to the concept image (first frame)
            duration: Optional custom duration for the video

        Returns:
            Path to the generated video
        """
        concept_path = Path(concept_image_path)
        if not concept_path.exists():
            raise FileNotFoundError(f"Concept image not found: {concept_image_path}")

        print(
            f"Unified video generation: Using concept image as reference: {concept_path}"
        )

        return self.generate_video(
            visual_prompt=visual_prompt,
            output_path=output_path,
            ref_img_path=concept_image_path,
            duration=duration,
            force_unified_mode=True,
        )
