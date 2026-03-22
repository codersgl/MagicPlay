"""
Professional Workflow Data Structures

These dataclasses define the data flow for the professional 6-stage
AI short drama director workflow:
1. Script Analysis - Identify characters and scenes
2. Reference Image Generation - Character (2:3) and Scene (16:9) images
3. Storyboard Design - First-frame prompts and motion prompts
4. First Frame Generation - Image-to-image with references
5. Video Generation - Image-to-video with first frames
6. Final Synthesis - Stitch, subtitles, music
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class CharacterRole(Enum):
    """Role of a character in the story."""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    EXTRA = "extra"


class SceneType(Enum):
    """Type of scene for video generation."""
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    TRANSITION = "transition"


@dataclass
class CharacterInfo:
    """Character information extracted from script analysis."""
    name: str
    visual_tags: List[str]  # For character anchor generation
    first_appearance: str  # Scene where character first appears
    role: CharacterRole  # protagonist, antagonist, supporting
    appearance_description: str = ""  # Physical appearance details
    clothing_style: str = ""  # Typical attire
    personality_traits: List[str] = field(default_factory=list)
    ai_prompt: str = ""  # English prompt for image generation

    def __post_init__(self):
        if isinstance(self.role, str):
            self.role = CharacterRole(self.role)


@dataclass
class SceneInfo:
    """Scene information extracted from script analysis."""
    scene_name: str
    setting: str  # INT./EXT. LOCATION - TIME
    scene_type: SceneType
    duration: int  # Estimated duration in seconds
    characters: List[str]  # Character names in this scene
    visual_requirements: str  # Mood, lighting, atmosphere
    key_elements: List[str] = field(default_factory=list)  # Props, furniture, etc.
    color_palette: str = ""  # Color scheme
    ai_prompt: str = ""  # English prompt for scene reference generation

    def __post_init__(self):
        if isinstance(self.scene_type, str):
            self.scene_type = SceneType(self.scene_type)


@dataclass
class ScriptAnalysisResult:
    """Complete result of script analysis Phase 1."""
    characters: List[CharacterInfo]
    scenes: List[SceneInfo]
    total_duration: int
    visual_style: str = ""  # Overall visual style (anime/realistic/etc.)
    genre: str = ""
    reasoning: str = ""  # Analysis reasoning

    @property
    def character_dict(self) -> Dict[str, CharacterInfo]:
        """Get characters as a dictionary keyed by name."""
        return {c.name: c for c in self.characters}

    @property
    def scene_dict(self) -> Dict[str, SceneInfo]:
        """Get scenes as a dictionary keyed by scene_name."""
        return {s.scene_name: s for s in self.scenes}


@dataclass
class CharacterReference:
    """Character reference image with metadata."""
    name: str
    anchor_image_path: Path  # 2:3 portrait
    character_info: CharacterInfo


@dataclass
class SceneReference:
    """Scene reference image with metadata."""
    scene_name: str
    reference_image_path: Path  # 16:9 landscape
    scene_info: SceneInfo


@dataclass
class StoryboardFrame:
    """A single frame in a storyboard."""
    frame_index: int
    start_second: int
    end_second: int
    first_frame_prompt: str  # I2I prompt for first frame generation
    motion_prompt: str  # Video generation prompt describing motion
    first_frame_path: Optional[Path] = None  # Generated first frame image
    video_segment_path: Optional[Path] = None  # Generated video segment
    characters: List[str] = field(default_factory=list)

    @property
    def duration(self) -> int:
        return self.end_second - self.start_second


@dataclass
class Storyboard:
    """Complete storyboard for a scene."""
    scene_name: str
    scene_reference_path: Path  # 16:9 scene reference
    frames: List[StoryboardFrame] = field(default_factory=list)
    total_duration: int = 0
    dialogue_lines: List[Dict[str, str]] = field(default_factory=list)  # [{"character": "...", "text": "..."}]

    def __post_init__(self):
        if self.frames and self.total_duration == 0:
            self.total_duration = self.frames[-1].end_second

    @property
    def clip_list_json(self) -> dict:
        """Convert to clip_list.json format."""
        clips = []
        for i, frame in enumerate(self.frames):
            clip = {
                "id": f"{self.scene_name}_frame_{i:02d}",
                "start_second": frame.start_second,
                "end_second": frame.end_second,
                "first_frame_prompt": frame.first_frame_prompt,
                "motion_prompt": frame.motion_prompt,
                "first_frame_image": str(frame.first_frame_path) if frame.first_frame_path else None,
                "video_segment": str(frame.video_segment_path) if frame.video_segment_path else None,
            }
            clips.append(clip)
        return {
            "scene_name": self.scene_name,
            "total_frames": len(self.frames),
            "total_duration": self.total_duration,
            "clips": clips
        }


@dataclass
class VideoClip:
    """A video clip with metadata for synthesis."""
    video_path: Path
    start_time: int  # Start time in final video
    end_time: int
    clip_id: str = ""
    first_frame_prompt: str = ""
    motion_prompt: str = ""
    subtitle_path: Optional[Path] = None
    transition: str = "cut"  # cut, fade, dissolve

    @property
    def duration(self) -> int:
        return self.end_time - self.start_time


@dataclass
class SubtitleCue:
    """A single subtitle cue for SRT generation."""
    index: int
    start_time: float  # In seconds
    end_time: float
    text: str
    character: str = ""

    def to_srt_format(self) -> str:
        """Convert to SRT format string."""
        start = self._format_timestamp(self.start_time)
        end = self._format_timestamp(self.end_time)
        return f"{self.index}\n{start} --> {end}\n{self.text}\n"

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to SRT timestamp HH:MM:SS,mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


@dataclass
class EpisodeProductionData:
    """Complete production data for an episode."""
    episode_name: str
    characters: Dict[str, CharacterReference] = field(default_factory=dict)
    scenes: Dict[str, SceneReference] = field(default_factory=dict)
    storyboards: Dict[str, Storyboard] = field(default_factory=dict)
    clip_list: List[VideoClip] = field(default_factory=list)
    subtitles: List[SubtitleCue] = field(default_factory=list)

    def to_clip_list_json(self) -> dict:
        """Convert entire episode to clip_list.json format."""
        all_clips = []
        for scene_name, storyboard in self.storyboards.items():
            all_clips.extend(storyboard.clip_list_json["clips"])
        return {
            "episode_name": self.episode_name,
            "total_scenes": len(self.storyboards),
            "total_clips": len(all_clips),
            "clips": all_clips
        }

    def save(self, output_dir: Path) -> None:
        """Save production data to directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Save clip list
        clip_list_path = output_dir / "clip_list.json"
        clip_list_path.write_text(
            json.dumps(self.to_clip_list_json(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        # Save subtitles
        if self.subtitles:
            srt_path = output_dir / "subtitles.srt"
            srt_content = "\n".join(cue.to_srt_format() for cue in self.subtitles)
            srt_path.write_text(srt_content, encoding="utf-8")

    @classmethod
    def from_clip_list_json(cls, episode_name: str, clip_list_path: Path) -> "EpisodeProductionData":
        """Load episode production data from clip_list.json."""
        import json
        data = json.loads(clip_list_path.read_text(encoding="utf-8"))
        instance = cls(episode_name=episode_name)
        for clip_data in data.get("clips", []):
            clip = VideoClip(
                video_path=Path(clip_data["video_segment"]) if clip_data.get("video_segment") else Path(""),
                start_time=clip_data["start_second"],
                end_time=clip_data["end_second"],
                clip_id=clip_data["id"],
                first_frame_prompt=clip_data.get("first_frame_prompt", ""),
                motion_prompt=clip_data.get("motion_prompt", ""),
            )
            instance.clip_list.append(clip)
        return instance
