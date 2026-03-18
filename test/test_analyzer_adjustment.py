"""
Pytest tests for ScriptAnalyzer parameter adjustment.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from magicplay.analyzer.script_analyzer import ScriptAnalyzer, SceneType


class TestScriptAnalyzerAdjustment:
    """Test ScriptAnalyzer parameter adjustments."""

    @pytest.fixture
    def sample_scene_script(self):
        """Sample scene script for testing."""
        return """
### SCENE HEADER
INT. LABORATORY - NIGHT

### VISUAL KEY
High-tech lab with holographic displays.

### SCRIPT BODY

**ACTION**
DR. ELARA stands before a massive console, fingers flying across holographic keys.

DR. ELARA
(muttering to herself)
Come on, stabilize... just a little longer...

**ACTION**
A warning light flashes red. An alarm begins to blare.

ASSISTANT
(rushing in)
Doctor! The containment field is collapsing!
"""

    def test_analyzer_adjustment_class(self):
        """Test adjusted analyzer class creation."""
        # Create analyzer with adjusted parameters
        class AdjustedScriptAnalyzer(ScriptAnalyzer):
            def _classify_scene_type(self, dialogue_lines: int, action_density: float, total_words: int) -> SceneType:
                """Adjusted classification for better scene type detection."""
                if total_words < 200:  # Increased from 100
                    return SceneType.TRANSITION
                
                dialogue_ratio = dialogue_lines / max(1, total_words / 15)  # Adjusted normalization
                
                if dialogue_ratio > 0.4 and action_density < 0.3:  # Adjusted thresholds
                    return SceneType.DIALOGUE
                elif action_density > 0.4 and dialogue_ratio < 0.4:  # Adjusted thresholds
                    return SceneType.ACTION
                elif dialogue_ratio < 0.15 and action_density < 0.2:
                    return SceneType.TRANSITION
                else:
                    return SceneType.MIXED
            
            def _estimate_duration(self, scene_type: SceneType, complexity_score: float, total_words: int) -> int:
                """Adjusted duration estimation with higher base durations."""
                # Increased base ranges by scene type
                ranges = {
                    SceneType.TRANSITION: (5, 8),
                    SceneType.DIALOGUE: (10, 18),  # Increased
                    SceneType.ACTION: (15, 30),    # Increased
                    SceneType.MIXED: (12, 25)      # Increased
                }
                
                min_dur, max_dur = ranges.get(scene_type, (10, 20))
                
                # Adjust by complexity
                duration = min_dur + (max_dur - min_dur) * complexity_score
                
                # Adjust by word count with stronger factor
                word_factor = min(2.0, total_words / 800)  # Adjusted: 800 words = 2x duration
                duration *= word_factor
                
                return int(round(duration))
        
        # Test creation
        analyzer = AdjustedScriptAnalyzer(min_duration=5, max_duration=30)
        assert analyzer.min_duration == 5
        assert analyzer.max_duration == 30

    def test_adjusted_scene_type_classification(self):
        """Test adjusted scene type classification logic."""
        # Create analyzer with adjusted parameters
        class AdjustedScriptAnalyzer(ScriptAnalyzer):
            def _classify_scene_type(self, dialogue_lines: int, action_density: float, total_words: int) -> SceneType:
                """Adjusted classification for better scene type detection."""
                if total_words < 200:
                    return SceneType.TRANSITION
                
                dialogue_ratio = dialogue_lines / max(1, total_words / 15)
                
                if dialogue_ratio > 0.4 and action_density < 0.3:
                    return SceneType.DIALOGUE
                elif action_density > 0.4 and dialogue_ratio < 0.4:
                    return SceneType.ACTION
                elif dialogue_ratio < 0.15 and action_density < 0.2:
                    return SceneType.TRANSITION
                else:
                    return SceneType.MIXED
        
        analyzer = AdjustedScriptAnalyzer(min_duration=5, max_duration=30)
        
        # Test each scene type classification
        test_cases = [
            (5, 0.1, 150, SceneType.TRANSITION),   # Few words, low action
            (20, 0.2, 500, SceneType.DIALOGUE),    # High dialogue ratio, low action
            (5, 0.5, 500, SceneType.ACTION),       # High action density
            (15, 0.3, 500, SceneType.MIXED),       # Balanced
            (10, 0.1, 800, SceneType.MIXED),       # Borderline case
        ]
        
        for dialogue_lines, action_density, total_words, expected_type in test_cases:
            scene_type = analyzer._classify_scene_type(dialogue_lines, action_density, total_words)
            assert scene_type == expected_type, f"Failed for {dialogue_lines}, {action_density}, {total_words}"

    def test_adjusted_duration_estimation(self):
        """Test adjusted duration estimation."""
        # Create analyzer with adjusted parameters
        class AdjustedScriptAnalyzer(ScriptAnalyzer):
            def _estimate_duration(self, scene_type: SceneType, complexity_score: float, total_words: int) -> int:
                """Adjusted duration estimation with higher base durations."""
                ranges = {
                    SceneType.TRANSITION: (5, 8),
                    SceneType.DIALOGUE: (10, 18),
                    SceneType.ACTION: (15, 30),
                    SceneType.MIXED: (12, 25)
                }
                
                min_dur, max_dur = ranges.get(scene_type, (10, 20))
                duration = min_dur + (max_dur - min_dur) * complexity_score
                word_factor = min(2.0, total_words / 800)
                duration *= word_factor
                
                return int(round(duration))
        
        analyzer = AdjustedScriptAnalyzer(min_duration=5, max_duration=30)
        
        # Test duration estimation for different parameters
        test_cases = [
            (SceneType.TRANSITION, 0.0, 100, 1),   # Minimum duration with word factor
            (SceneType.DIALOGUE, 0.5, 400, 7),     # Medium complexity with word factor
            (SceneType.ACTION, 1.0, 800, 30),      # Maximum complexity and word factor
            (SceneType.MIXED, 0.8, 1200, 34),      # High word count (capped at 2x)
        ]
        
        for scene_type, complexity, total_words, expected_duration in test_cases:
            duration = analyzer._estimate_duration(scene_type, complexity, total_words)
            # Allow some rounding tolerance
            assert abs(duration - expected_duration) <= 2, f"Failed for {scene_type}, {complexity}, {total_words}: got {duration}, expected {expected_duration}"

    def test_adjusted_analyzer_with_sample_script(self, sample_scene_script):
        """Test adjusted analyzer with a sample script."""
        # Create analyzer with adjusted parameters
        class AdjustedScriptAnalyzer(ScriptAnalyzer):
            def _classify_scene_type(self, dialogue_lines: int, action_density: float, total_words: int) -> SceneType:
                """Adjusted classification."""
                if total_words < 200:
                    return SceneType.TRANSITION
                
                dialogue_ratio = dialogue_lines / max(1, total_words / 15)
                
                if dialogue_ratio > 0.4 and action_density < 0.3:
                    return SceneType.DIALOGUE
                elif action_density > 0.4 and dialogue_ratio < 0.4:
                    return SceneType.ACTION
                elif dialogue_ratio < 0.15 and action_density < 0.2:
                    return SceneType.TRANSITION
                else:
                    return SceneType.MIXED
        
        analyzer = AdjustedScriptAnalyzer(min_duration=5, max_duration=30)
        result = analyzer.analyze(sample_scene_script)
        
        # Verify basic properties
        assert isinstance(result, object)  # Should be AnalysisResult
        assert hasattr(result, 'total_words')
        assert hasattr(result, 'dialogue_lines')
        assert hasattr(result, 'action_density')
        assert hasattr(result, 'scene_type')
        assert hasattr(result, 'estimated_duration')
        
        # Duration should be within configured range
        assert analyzer.min_duration <= result.estimated_duration <= analyzer.max_duration

    def test_adjusted_analyzer_short_dialogue(self):
        """Test adjusted analyzer with short dialogue script."""
        short_script = """
### SCENE HEADER
INT. OFFICE - DAY

### SCRIPT BODY

JOHN
Good morning.

MARY
Morning. Ready for the meeting?
"""
        
        # Create analyzer with adjusted parameters
        class AdjustedScriptAnalyzer(ScriptAnalyzer):
            def _classify_scene_type(self, dialogue_lines: int, action_density: float, total_words: int) -> SceneType:
                """Adjusted classification."""
                if total_words < 200:
                    return SceneType.TRANSITION
                
                dialogue_ratio = dialogue_lines / max(1, total_words / 15)
                
                if dialogue_ratio > 0.4 and action_density < 0.3:
                    return SceneType.DIALOGUE
                elif action_density > 0.4 and dialogue_ratio < 0.4:
                    return SceneType.ACTION
                elif dialogue_ratio < 0.15 and action_density < 0.2:
                    return SceneType.TRANSITION
                else:
                    return SceneType.MIXED
        
        analyzer = AdjustedScriptAnalyzer(min_duration=5, max_duration=30)
        result = analyzer.analyze(short_script)
        
        # Short script should be classified as TRANSITION (less than 200 words)
        # or possibly DIALOGUE depending on actual word count
        assert result.total_words < 200  # Should be few words
        
        # Duration should be reasonable
        assert analyzer.min_duration <= result.estimated_duration <= analyzer.max_duration

    def test_word_factor_capping(self):
        """Test that word factor is capped at 2.0."""
        # Create analyzer with adjusted parameters
        class AdjustedScriptAnalyzer(ScriptAnalyzer):
            def _estimate_duration(self, scene_type: SceneType, complexity_score: float, total_words: int) -> int:
                """Adjusted duration estimation."""
                ranges = {
                    SceneType.TRANSITION: (5, 8),
                    SceneType.DIALOGUE: (10, 18),
                    SceneType.ACTION: (15, 30),
                    SceneType.MIXED: (12, 25)
                }
                
                min_dur, max_dur = ranges.get(scene_type, (10, 20))
                duration = min_dur + (max_dur - min_dur) * complexity_score
                word_factor = min(2.0, total_words / 800)
                duration *= word_factor
                
                return int(round(duration))
        
        analyzer = AdjustedScriptAnalyzer(min_duration=5, max_duration=30)
        
        # Test with very high word count (should be capped at 2x)
        duration_800 = analyzer._estimate_duration(SceneType.DIALOGUE, 0.5, 800)
        duration_1600 = analyzer._estimate_duration(SceneType.DIALOGUE, 0.5, 1600)
        duration_2400 = analyzer._estimate_duration(SceneType.DIALOGUE, 0.5, 2400)
        
        # 1600 and 2400 should have similar duration (both capped at 2x)
        # 800 should have lower duration
        assert duration_800 < duration_1600
        assert abs(duration_1600 - duration_2400) <= 2  # Should be similar due to cap

    def test_complexity_score_effect(self):
        """Test that complexity score affects duration appropriately."""
        # Create analyzer with adjusted parameters
        class AdjustedScriptAnalyzer(ScriptAnalyzer):
            def _estimate_duration(self, scene_type: SceneType, complexity_score: float, total_words: int) -> int:
                """Adjusted duration estimation."""
                ranges = {
                    SceneType.TRANSITION: (5, 8),
                    SceneType.DIALOGUE: (10, 18),
                    SceneType.ACTION: (15, 30),
                    SceneType.MIXED: (12, 25)
                }
                
                min_dur, max_dur = ranges.get(scene_type, (10, 20))
                duration = min_dur + (max_dur - min_dur) * complexity_score
                word_factor = min(2.0, total_words / 800)
                duration *= word_factor
                
                return int(round(duration))
        
        analyzer = AdjustedScriptAnalyzer(min_duration=5, max_duration=30)
        
        # Test with increasing complexity scores
        duration_low = analyzer._estimate_duration(SceneType.DIALOGUE, 0.0, 400)
        duration_medium = analyzer._estimate_duration(SceneType.DIALOGUE, 0.5, 400)
        duration_high = analyzer._estimate_duration(SceneType.DIALOGUE, 1.0, 400)
        
        # Duration should increase with complexity
        assert duration_low < duration_medium
        assert duration_medium < duration_high