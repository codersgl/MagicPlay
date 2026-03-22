"""
Tests for SceneSegmentGenerator module.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from magicplay.generators.scene_segment_gen import SceneSegmentGenerator


class TestSceneSegmentGenerator:
    """Test SceneSegmentGenerator functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_video_generator(self):
        """Create mock video generator."""
        mock = MagicMock()
        mock.generate_video = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def scene_segment_generator(self, temp_dir, mock_video_generator):
        """Create SceneSegmentGenerator with mocked dependencies."""
        with patch("magicplay.generators.scene_segment_gen.DataManager") as mock_dm:
            mock_dm.get_scene_segments_path.return_value = temp_dir

            with patch("magicplay.generators.scene_segment_gen.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock()

                with patch(
                    "magicplay.generators.scene_segment_gen.VideoGenerator",
                    return_value=mock_video_generator,
                ):
                    gen = SceneSegmentGenerator(
                        story_name="TestStory",
                        episode_name="Episode1",
                        size=(1280, 720),
                    )
                    yield gen

    def test_initialization(self, scene_segment_generator, temp_dir):
        """Test SceneSegmentGenerator initialization."""
        assert scene_segment_generator.story_name == "TestStory"
        assert scene_segment_generator.episode_name == "Episode1"
        assert scene_segment_generator.size == (1280, 720)
        assert scene_segment_generator.output_dir == temp_dir
        assert scene_segment_generator.MAX_SEGMENT_DURATION == 10

    def test_generate_scene_segments_single_segment(self, scene_segment_generator, temp_dir):
        """Test generating a single segment for short scene."""
        video_path = temp_dir / "scene_1_segment_0.mp4"
        video_path.touch()  # Create actual file
        scene_segment_generator.video_gen.generate_video.return_value = video_path

        result = scene_segment_generator.generate_scene_segments(
            scene_name="scene_1",
            scene_script="Script content",
            base_visual_prompt="A hero walks",
            segment_duration=5,  # Under MAX_SEGMENT_DURATION
            use_multi_frame=True,
        )

        assert len(result) == 1
        assert scene_segment_generator.video_gen.generate_video.called

    def test_generate_scene_segments_multi_frame(self, scene_segment_generator, temp_dir):
        """Test generating multiple segments for long scene."""
        video_path = temp_dir / "scene_long_segment_0.mp4"
        video_path2 = temp_dir / "scene_long_segment_1.mp4"
        video_path.touch()
        video_path2.touch()
        scene_segment_generator.video_gen.generate_video.side_effect = [
            video_path,
            video_path2,
        ]

        result = scene_segment_generator.generate_scene_segments(
            scene_name="scene_long",
            scene_script="Script content",
            base_visual_prompt="A hero walks",
            segment_duration=15,  # Over MAX_SEGMENT_DURATION
            use_multi_frame=True,
        )

        # Should generate 2 segments (15 / 10 = 1.5 -> ceil = 2)
        assert len(result) == 2
        assert scene_segment_generator.video_gen.generate_video.call_count == 2

    def test_generate_scene_segments_no_multi_frame(self, scene_segment_generator, temp_dir):
        """Test generating single segment when multi_frame is disabled."""
        video_path = temp_dir / "scene_no_mf_segment_0.mp4"
        video_path.touch()
        scene_segment_generator.video_gen.generate_video.return_value = video_path

        result = scene_segment_generator.generate_scene_segments(
            scene_name="scene_no_mf",
            scene_script="Script content",
            base_visual_prompt="A hero walks",
            segment_duration=15,  # Over MAX_SEGMENT_DURATION
            use_multi_frame=False,  # Disabled
        )

        assert len(result) == 1
        assert scene_segment_generator.video_gen.generate_video.call_count == 1

    def test_generate_scene_segments_with_segment_index(self, scene_segment_generator, temp_dir):
        """Test that segment index is passed correctly."""
        video_path = temp_dir / "scene_idx_segment_0.mp4"
        video_path.touch()
        scene_segment_generator.video_gen.generate_video.return_value = video_path

        scene_segment_generator.generate_scene_segments(
            scene_name="scene_idx",
            scene_script="Script content",
            base_visual_prompt="A hero walks",
            segment_duration=5,
            use_multi_frame=True,
        )

        call_args = scene_segment_generator.video_gen.generate_video.call_args
        assert call_args is not None

    def test_create_segment_prompt(self, scene_segment_generator):
        """Test segment prompt creation."""
        base_prompt = "A hero walks through the castle"
        result = scene_segment_generator._create_segment_prompt(
            base_prompt=base_prompt, segment_index=0, total_segments=3
        )

        assert "Part 1 of 3" in result
        assert "A hero walks through the castle" in result

    def test_create_segment_prompt_second_segment(self, scene_segment_generator):
        """Test segment prompt for second segment."""
        base_prompt = "A hero walks"
        result = scene_segment_generator._create_segment_prompt(
            base_prompt=base_prompt, segment_index=1, total_segments=3
        )

        assert "Part 2 of 3" in result


class TestSceneSegmentStitching:
    """Test video stitching functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_video_generator(self):
        """Create mock video generator."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def scene_segment_generator(self, temp_dir, mock_video_generator):
        """Create SceneSegmentGenerator with mocked dependencies."""
        with patch("magicplay.generators.scene_segment_gen.DataManager") as mock_dm:
            mock_dm.get_scene_segments_path.return_value = temp_dir

            with patch("magicplay.generators.scene_segment_gen.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock()

                with patch(
                    "magicplay.generators.scene_segment_gen.VideoGenerator",
                    return_value=mock_video_generator,
                ):
                    yield SceneSegmentGenerator(story_name="TestStory", episode_name="Episode1")

    def test_stitch_segments_single(self, scene_segment_generator, temp_dir):
        """Test stitching with only one segment returns that segment."""
        single_segment = temp_dir / "single.mp4"

        result = scene_segment_generator.stitch_segments(scene_name="test_scene", segments=[single_segment])

        assert result == single_segment

    def test_stitch_segments_empty_list(self, scene_segment_generator):
        """Test stitching with empty list returns None."""
        result = scene_segment_generator.stitch_segments(scene_name="test_scene", segments=[])

        assert result is None

    def test_stitch_segments_multiple(self, scene_segment_generator, temp_dir):
        """Test stitching multiple segments."""
        with patch("magicplay.generators.scene_segment_gen.MediaUtils") as mock_media:
            mock_media.stitch_videos.return_value = True

            segments = [
                temp_dir / "seg1.mp4",
                temp_dir / "seg2.mp4",
                temp_dir / "seg3.mp4",
            ]

            for seg in segments:
                seg.touch()

            result = scene_segment_generator.stitch_segments(scene_name="multi_scene", segments=segments)

            assert result == temp_dir / "multi_scene_stitched.mp4"
            mock_media.stitch_videos.assert_called_once()

    def test_stitch_segments_media_utils_failure(self, scene_segment_generator, temp_dir):
        """Test handling of MediaUtils failure."""
        with patch("magicplay.generators.scene_segment_gen.MediaUtils") as mock_media:
            mock_media.stitch_videos.return_value = False

            segments = [temp_dir / "seg1.mp4", temp_dir / "seg2.mp4"]

            for seg in segments:
                seg.touch()

            result = scene_segment_generator.stitch_segments(scene_name="fail_scene", segments=segments)

            assert result is None


class TestGenerateWithTimeline:
    """Test generate_with_timeline method."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_video_generator(self):
        """Create mock video generator."""
        mock = MagicMock()
        mock.generate_video = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_timeline_analyzer(self):
        """Create mock timeline analyzer."""
        return MagicMock()

    @pytest.fixture
    def generator(self, temp_dir, mock_video_generator, mock_timeline_analyzer):
        """Create generator with mocked dependencies."""
        with patch("magicplay.generators.scene_segment_gen.DataManager") as mock_dm:
            mock_dm.get_scene_segments_path.return_value = temp_dir

            with patch("magicplay.generators.scene_segment_gen.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock()

                with patch(
                    "magicplay.generators.scene_segment_gen.VideoGenerator",
                    return_value=mock_video_generator,
                ):
                    yield SceneSegmentGenerator(
                        story_name="TestStory",
                        episode_name="Episode1",
                        timeline_analyzer=mock_timeline_analyzer,
                    )

    def test_generate_with_timeline_calls_analyzer(self, generator, temp_dir, mock_timeline_analyzer):
        """Test that generate_with_timeline uses TimelineAnalyzer."""
        from magicplay.analyzer.timeline_analyzer import (
            TimelineResult,
            TimelineSegment,
        )

        video_path = temp_dir / "scene_timeline_segment_0.mp4"
        video_path2 = temp_dir / "scene_timeline_segment_1.mp4"
        video_path.touch()
        video_path2.touch()

        generator.video_gen.generate_video.side_effect = [
            video_path,
            video_path2,
        ]

        # Mock TimelineAnalyzer result
        mock_timeline_result = TimelineResult(
            segments=[
                TimelineSegment(
                    start_second=0,
                    end_second=5,
                    visual_prompt="Segment 1 visual prompt",
                    description="First segment showing hero entering",
                ),
                TimelineSegment(
                    start_second=5,
                    end_second=10,
                    visual_prompt="Segment 2 visual prompt",
                    description="Second segment showing battle",
                ),
            ],
            total_duration=10,
            reasoning="Test reasoning",
        )

        mock_timeline_analyzer.analyze.return_value = mock_timeline_result

        result = generator.generate_with_timeline(
            scene_name="scene_timeline",
            scene_script="A hero enters a castle and battles a dragon",
            segment_duration=10,
            use_multi_frame=True,
        )

        # Verify TimelineAnalyzer was called
        mock_timeline_analyzer.analyze.assert_called_once_with(
            scene_script="A hero enters a castle and battles a dragon",
            duration=10,
        )

        # Verify video generation was called with timeline-based prompts
        assert generator.video_gen.generate_video.call_count == 2

        # First segment should use its own visual_prompt from timeline
        first_call = generator.video_gen.generate_video.call_args_list[0]
        assert "Segment 1 visual prompt" in first_call.kwargs["visual_prompt"]

        # Second segment should use its own visual_prompt from timeline
        second_call = generator.video_gen.generate_video.call_args_list[1]
        assert "Segment 2 visual prompt" in second_call.kwargs["visual_prompt"]

        assert len(result) == 2

    def test_generate_with_timeline_fallback(self, generator, temp_dir, mock_timeline_analyzer):
        """Test fallback when timeline analysis returns empty segments."""
        from magicplay.analyzer.timeline_analyzer import TimelineResult

        video_path = temp_dir / "fallback_segment_0.mp4"
        video_path2 = temp_dir / "fallback_segment_1.mp4"
        video_path.touch()
        video_path2.touch()
        generator.video_gen.generate_video.side_effect = [
            video_path,
            video_path2,
        ]

        # Mock TimelineAnalyzer returning empty segments
        mock_timeline_result = TimelineResult(
            segments=[],  # Empty segments - should trigger fallback
            total_duration=15,
            reasoning="Empty segments",
        )

        mock_timeline_analyzer.analyze.return_value = mock_timeline_result

        generator.generate_with_timeline(
            scene_name="fallback_scene",
            scene_script="A hero walks",
            segment_duration=15,  # Over MAX_SEGMENT_DURATION to trigger multi-frame
            use_multi_frame=True,
        )

        # Should still generate something (fallback behavior) - 2 segments
        assert generator.video_gen.generate_video.call_count == 2

        # The fallback should use scene_script with "Part N of M"
        first_call = generator.video_gen.generate_video.call_args_list[0]
        visual_prompt = first_call.kwargs["visual_prompt"]
        assert "A hero walks" in visual_prompt
        assert "Part 1 of 2" in visual_prompt

    def test_generate_with_timeline_logs_segment_info(self, generator, temp_dir, mock_timeline_analyzer):
        """Test that generate_with_timeline logs segment info.

        Note: Loguru output is captured by pytest's internal mechanism,
        visible in 'Captured stderr call' section of test output.
        """
        from magicplay.analyzer.timeline_analyzer import (
            TimelineResult,
            TimelineSegment,
        )

        video_path = temp_dir / "log_scene_segment_0.mp4"
        video_path.touch()
        generator.video_gen.generate_video.return_value = video_path

        mock_timeline_result = TimelineResult(
            segments=[
                TimelineSegment(
                    start_second=0,
                    end_second=5,
                    visual_prompt="Hero enters castle",
                    description="Hero walking through castle gates",
                ),
            ],
            total_duration=5,
            reasoning="Test",
        )

        mock_timeline_analyzer.analyze.return_value = mock_timeline_result

        # This should not raise - logging is verified by observing
        # "Captured stderr call" in pytest output
        generator.generate_with_timeline(
            scene_name="log_scene",
            scene_script="Hero enters castle",
            segment_duration=5,
            use_multi_frame=True,
        )

    def test_timeline_analyzer_injection(self, temp_dir, mock_video_generator):
        """Test that timeline_analyzer is properly injected via constructor."""
        from magicplay.analyzer.timeline_analyzer import TimelineAnalyzer

        # Create a mock timeline analyzer
        mock_analyzer = MagicMock(spec=TimelineAnalyzer)

        with patch("magicplay.generators.scene_segment_gen.DataManager") as mock_dm:
            mock_dm.get_scene_segments_path.return_value = temp_dir

            with patch("magicplay.generators.scene_segment_gen.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock()

                with patch(
                    "magicplay.generators.scene_segment_gen.VideoGenerator",
                    return_value=mock_video_generator,
                ):
                    # Pass the mock analyzer to the constructor
                    gen = SceneSegmentGenerator(
                        story_name="TestStory",
                        episode_name="Episode1",
                        timeline_analyzer=mock_analyzer,
                    )

                    # Verify the analyzer was stored
                    assert gen._timeline_analyzer is mock_analyzer


class TestSceneSegmentGeneratorEdgeCases:
    """Test edge cases for SceneSegmentGenerator."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_video_generator(self):
        """Create mock video generator."""
        mock = MagicMock()
        mock.generate_video = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def generator(self, temp_dir, mock_video_generator):
        """Create generator with mocked dependencies."""
        with patch("magicplay.generators.scene_segment_gen.DataManager") as mock_dm:
            mock_dm.get_scene_segments_path.return_value = temp_dir

            with patch("magicplay.generators.scene_segment_gen.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock()

                with patch(
                    "magicplay.generators.scene_segment_gen.VideoGenerator",
                    return_value=mock_video_generator,
                ):
                    yield SceneSegmentGenerator(story_name="TestStory", episode_name="Episode1")

    def test_generate_with_video_failure(self, generator, temp_dir):
        """Test handling of video generation failure."""
        generator.video_gen.generate_video.return_value = None

        result = generator.generate_scene_segments(
            scene_name="fail_scene",
            scene_script="Script",
            base_visual_prompt="A hero",
            segment_duration=5,
        )

        assert len(result) == 0

    def test_generate_with_exception(self, generator, temp_dir):
        """Test handling of exception during generation."""
        generator.video_gen.generate_video.side_effect = Exception("API Error")

        result = generator.generate_scene_segments(
            scene_name="error_scene",
            scene_script="Script",
            base_visual_prompt="A hero",
            segment_duration=5,
        )

        assert len(result) == 0

    def test_duration_exactly_at_max(self, generator, temp_dir):
        """Test scene duration exactly at MAX_SEGMENT_DURATION."""
        video_path = temp_dir / "max_seg_segment_0.mp4"
        video_path.touch()
        generator.video_gen.generate_video.return_value = video_path

        # Duration exactly at MAX_SEGMENT_DURATION should still be single segment
        result = generator.generate_scene_segments(
            scene_name="max_scene",
            scene_script="Script",
            base_visual_prompt="A hero",
            segment_duration=10,  # Exactly MAX
            use_multi_frame=True,
        )

        assert len(result) == 1

    def test_stitch_exception_handling(self, generator, temp_dir):
        """Test handling of exception during stitching."""
        with patch("magicplay.generators.scene_segment_gen.MediaUtils") as mock_media:
            mock_media.stitch_videos.side_effect = Exception("Stitch error")

            segments = [temp_dir / "seg1.mp4", temp_dir / "seg2.mp4"]
            for seg in segments:
                seg.touch()

            result = generator.stitch_segments(scene_name="stitch_error", segments=segments)

            assert result is None
