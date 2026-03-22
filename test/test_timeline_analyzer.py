"""
Pytest tests for TimelineAnalyzer.
"""

from unittest.mock import MagicMock

import pytest

from magicplay.analyzer.timeline_analyzer import (
    TimelineAnalyzer,
    TimelineResult,
)


class TestTimelineAnalyzer:
    """Test TimelineAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create a TimelineAnalyzer instance for tests."""
        return TimelineAnalyzer()

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        mock = MagicMock()
        mock.generate_content.return_value = '{"segments": [], "reasoning": "test"}'
        return mock

    def test_analyze_returns_timeline_result(self, analyzer):
        """Test that analyze returns a TimelineResult instance."""
        scene_script = """场景：角色在森林中行走，突然遇到一只怪兽。

VISUAL KEY:
森林中小径蜿蜒，角色从左侧入镜，..."""
        result = analyzer.analyze(scene_script, duration=10)

        assert isinstance(result, TimelineResult)
        assert result.total_duration == 10

    def test_analyze_with_mock_llm(self, mock_llm_service):
        """Test analyze with a mock LLM service."""
        analyzer = TimelineAnalyzer(llm_service=mock_llm_service)

        # Set up mock response
        mock_response = """{
            "segments": [
                {"start_second": 0, "end_second": 5,
                 "visual_prompt": "角色行走在森林小径上",
                 "description": "角色从左侧进入画面"},
                {"start_second": 5, "end_second": 10,
                 "visual_prompt": "角色突然停下，怪兽出现",
                 "description": "怪兽从树后出现"}
            ],
            "reasoning": "将10秒视频分为两个5秒片段"
        }"""
        mock_llm_service.generate_content.return_value = mock_response

        scene_script = "场景：角色在森林中行走，突然遇到一只怪兽。"
        result = analyzer.analyze(scene_script, duration=10)

        assert isinstance(result, TimelineResult)
        assert result.total_duration == 10
        assert len(result.segments) == 2
        assert result.segments[0].start_second == 0

    def test_segment_has_required_fields(self):
        """Test that each segment has all required fields."""
        # Create analyzer with mock that returns proper JSON
        mock_llm = MagicMock()
        mock_response = """{
            "segments": [
                {"start_second": 0, "end_second": 5, "visual_prompt": "角色挥手", "description": "角色从左侧进入"}
            ],
            "reasoning": "简单的挥手动作"
        }"""
        mock_llm.generate_content.return_value = mock_response

        analyzer = TimelineAnalyzer(llm_service=mock_llm)
        result = analyzer.analyze("场景：角色挥手。", duration=5)

        seg = result.segments[0]
        assert hasattr(seg, "start_second")
        assert hasattr(seg, "end_second")
        assert hasattr(seg, "visual_prompt")
        assert hasattr(seg, "description")

    def test_segment_minimum_duration(self):
        """Test that segments have minimum 3 second duration."""
        mock_llm = MagicMock()
        mock_response = """{
            "segments": [
                {"start_second": 0, "end_second": 4, "visual_prompt": "动作1", "description": "描述1"},
                {"start_second": 4, "end_second": 8, "visual_prompt": "动作2", "description": "描述2"}
            ],
            "reasoning": "测试"
        }"""
        mock_llm.generate_content.return_value = mock_response

        analyzer = TimelineAnalyzer(llm_service=mock_llm)
        result = analyzer.analyze("场景：两个动作。", duration=8)

        # Both segments should be at least 3 seconds
        for seg in result.segments:
            assert seg.end_second - seg.start_second >= 3

    def test_first_segment_starts_at_zero(self):
        """Test that the first segment starts at second 0."""
        mock_llm = MagicMock()
        mock_response = """{
            "segments": [
                {"start_second": 0, "end_second": 5, "visual_prompt": "开始动作", "description": "开始"}
            ],
            "reasoning": "测试"
        }"""
        mock_llm.generate_content.return_value = mock_response

        analyzer = TimelineAnalyzer(llm_service=mock_llm)
        result = analyzer.analyze("场景：开始。", duration=5)

        assert result.segments[0].start_second == 0

    def test_segments_cover_total_duration(self):
        """Test that segment end times cover the total duration."""
        mock_llm = MagicMock()
        mock_response = """{
            "segments": [
                {"start_second": 0, "end_second": 5, "visual_prompt": "第一段", "description": "第一段"},
                {"start_second": 5, "end_second": 10, "visual_prompt": "第二段", "description": "第二段"}
            ],
            "reasoning": "完整覆盖10秒"
        }"""
        mock_llm.generate_content.return_value = mock_response

        analyzer = TimelineAnalyzer(llm_service=mock_llm)
        result = analyzer.analyze("场景：两个动作。", duration=10)

        # Last segment should end at total_duration
        last_seg = result.segments[-1]
        assert last_seg.end_second == result.total_duration

    def test_parse_invalid_json_returns_error_result(self):
        """Test that invalid JSON returns a TimelineResult with error info."""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value = "这不是有效的JSON"

        analyzer = TimelineAnalyzer(llm_service=mock_llm)

        # The analyzer should handle invalid JSON gracefully
        result = analyzer.analyze("场景：测试。", duration=5)

        # Result should still be a TimelineResult, but may have empty segments
        assert isinstance(result, TimelineResult)

    def test_analyze_empty_scene_script(self):
        """Test analyzing empty scene script."""
        mock_llm = MagicMock()
        mock_response = """{
            "segments": [
                {"start_second": 0, "end_second": 5, "visual_prompt": "空场景", "description": "空"}
            ],
            "reasoning": "空场景"
        }"""
        mock_llm.generate_content.return_value = mock_response

        analyzer = TimelineAnalyzer(llm_service=mock_llm)
        result = analyzer.analyze("", duration=5)

        assert isinstance(result, TimelineResult)
        assert result.total_duration == 5

    def test_visual_prompt_is_not_empty(self):
        """Test that visual prompts are not empty strings."""
        mock_llm = MagicMock()
        mock_response = """{
            "segments": [
                {"start_second": 0, "end_second": 5, "visual_prompt": "角色行走在森林中", "description": "角色行走"},
                {"start_second": 5, "end_second": 10, "visual_prompt": "角色突然停下", "description": "突然停下"}
            ],
            "reasoning": "两个清晰的动作"
        }"""
        mock_llm.generate_content.return_value = mock_response

        analyzer = TimelineAnalyzer(llm_service=mock_llm)
        result = analyzer.analyze("场景：行走和停下。", duration=10)

        for seg in result.segments:
            assert seg.visual_prompt is not None
            assert len(seg.visual_prompt) > 0

    def test_reasoning_is_tracked(self):
        """Test that the reasoning from LLM is preserved in result."""
        mock_llm = MagicMock()
        test_reasoning = "这是详细的分镜推理过程"
        mock_response = f"""{{
            "segments": [
                {{"start_second": 0, "end_second": 5, "visual_prompt": "动作", "description": "描述"}}
            ],
            "reasoning": "{test_reasoning}"
        }}"""
        mock_llm.generate_content.return_value = mock_response

        analyzer = TimelineAnalyzer(llm_service=mock_llm)
        result = analyzer.analyze("场景：测试。", duration=5)

        assert result.reasoning == test_reasoning
