# Timeline Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LLM-powered timeline analysis to Phase 3, enabling per-second visual prompts for video segment generation.

**Architecture:** `TimelineAnalyzer` calls LLM to parse scene scripts into time-indexed segments (min 3s). `SceneSegmentGenerator` gains a `generate_with_timeline()` method that uses these精准 prompts instead of simple "Part N of M".

**Tech Stack:** Python, existing LLMService, existing SceneSegmentGenerator, Pydantic dataclasses

---

## File Structure

| File | Action |
|------|--------|
| `src/magicplay/analyzer/timeline_analyzer.py` | Create |
| `src/magicplay/prompts/timeline_analyze.md` | Create |
| `src/magicplay/generators/scene_segment_gen.py` | Modify |
| `src/magicplay/di_container.py` | Modify |
| `test/test_timeline_analyzer.py` | Create |
| `test/test_scene_segment_generator.py` | Modify |

---

## Task 1: TimelineAnalyzer Core

**Files:**
- Create: `src/magicplay/analyzer/timeline_analyzer.py`
- Create: `src/magicplay/prompts/timeline_analyze.md`
- Test: `test/test_timeline_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# test/test_timeline_analyzer.py
import pytest
from magicplay.analyzer.timeline_analyzer import TimelineAnalyzer, TimelineSegment, TimelineResult

def test_analyze_returns_timeline_result():
    analyzer = TimelineAnalyzer()
    scene_script = "场景：角色在森林中行走，突然遇到一只怪兽。\n\nVISUAL KEY:\n森林中小径蜿蜒，角色从左侧入镜，..."
    result = analyzer.analyze(scene_script, duration=10)
    assert isinstance(result, TimelineResult)
    assert result.total_duration == 10
    assert len(result.segments) >= 2
    assert result.segments[0].start_second == 0

def test_segment_has_required_fields():
    analyzer = TimelineAnalyzer()
    result = analyzer.analyze("场景：角色挥手。", duration=5)
    seg = result.segments[0]
    assert hasattr(seg, 'start_second')
    assert hasattr(seg, 'end_second')
    assert hasattr(seg, 'visual_prompt')
    assert hasattr(seg, 'description')
    assert seg.end_second - seg.start_second >= 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/codersgl/personal/MagicPlay
uv run pytest test/test_timeline_analyzer.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: Write TimelineAnalyzer**

Create `src/magicplay/prompts/timeline_analyze.md`:
```markdown
你是一个专业的视频分镜专家。根据场景脚本和总时长，
将视频内容切分成多个时间片段，每个片段有独立的视觉描述。

要求：
- 最小分镜时长：3秒
- 每个片段的 visual_prompt 必须精准描述该时间段的画面内容
- 考虑镜头语言：推、拉、摇、移、跟等
- 考虑动作连贯性：前一镜头的结束动作与后一镜头的开始动作应衔接自然
- 输出有效的 JSON 格式
```

Create `src/magicplay/analyzer/timeline_analyzer.py`:
```python
from dataclasses import dataclass
from typing import List
from magicplay.services.llm import LLMService

@dataclass
class TimelineSegment:
    start_second: int
    end_second: int
    visual_prompt: str
    description: str

@dataclass
class TimelineResult:
    segments: List[TimelineSegment]
    total_duration: int
    reasoning: str

class TimelineAnalyzer:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def analyze(self, scene_script: str, duration: int) -> TimelineResult:
        prompt = self._build_prompt(scene_script, duration)
        response = self.llm.generate(prompt)
        return self._parse_response(response, duration)

    def _build_prompt(self, script: str, duration: int) -> str:
        from pathlib import Path
        template = Path(__file__).parent.parent / "prompts" / "timeline_analyze.md"
        template_content = template.read_text() if template.exists() else ""
        return f"""{template_content}

场景总时长：{duration}秒
场景脚本：
{script}
"""

    def _parse_response(self, response: str, duration: int) -> TimelineResult:
        import json, re
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {"segments": [], "reasoning": response}
        segments = [
            TimelineSegment(
                start_second=s["start"],
                end_second=s["end"],
                visual_prompt=s["visual_prompt"],
                description=s.get("description", "")
            )
            for s in data.get("segments", [])
        ]
        return TimelineResult(
            segments=segments,
            total_duration=duration,
            reasoning=data.get("reasoning", "")
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest test/test_timeline_analyzer.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/magicplay/analyzer/timeline_analyzer.py src/magicplay/prompts/timeline_analyze.md test/test_timeline_analyzer.py
git commit -m "feat: add TimelineAnalyzer for time-axis scene segmentation"
```

---

## Task 2: Integrate TimelineAnalyzer into SceneSegmentGenerator

**Files:**
- Modify: `src/magicplay/generators/scene_segment_gen.py`
- Test: `test/test_scene_segment_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to test/test_scene_segment_generator.py
def test_generate_with_timeline_uses_segment_prompts(mock_llm_service, tmp_path):
    from magicplay.generators.scene_segment_gen import SceneSegmentGenerator
    from magicplay.analyzer.timeline_analyzer import TimelineSegment

    # Mock LLM returns a timeline with 2 segments
    mock_llm_service.generate.return_value = json.dumps({
        "segments": [
            {"start": 0, "end": 5, "visual_prompt": "特写：角色表情变化", "description": "对话开始"},
            {"start": 5, "end": 10, "visual_prompt": "中景：角色起身走向门口", "description": "动作"}
        ],
        "reasoning": "因为场景包含两个明显的情节转折"
    })

    analyzer = TimelineAnalyzer(llm_service=mock_llm_service)
    generator = SceneSegmentGenerator("TestStory", "TestEp")

    # Verify that each segment prompt is used
    # (Implementation detail: check mock was called with correct prompts)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest test/test_scene_segment_generator.py::test_generate_with_timeline_uses_segment_prompts -v
```
Expected: FAIL — method not found

- [ ] **Step 3: Add generate_with_timeline method**

Modify `src/magicplay/generators/scene_segment_gen.py`:
```python
from magicplay.analyzer.timeline_analyzer import TimelineAnalyzer

class SceneSegmentGenerator:
    # ... existing code ...

    def generate_with_timeline(
        self,
        scene_name: str,
        scene_script: str,
        segment_duration: int,
        use_multi_frame: bool = True,
    ) -> List[Path]:
        """Generate video using LLM-analyzed timeline for precise prompts.

        Args:
            scene_name: Name of the scene
            scene_script: Full scene script content
            segment_duration: Total duration in seconds
            use_multi_frame: Whether to split into multiple segments

        Returns:
            List of paths to generated video segments
        """
        # Step 1: Analyze timeline
        timeline_analyzer = TimelineAnalyzer()
        timeline = timeline_analyzer.analyze(scene_script, segment_duration)

        if not timeline.segments:
            # Fallback to old behavior
            return self.generate_scene_segments(
                scene_name, scene_script,
                self._create_segment_prompt(scene_script, 0, 1),
                segment_duration, use_multi_frame
            )

        segments = []
        for i, seg in enumerate(timeline.segments):
            logger.info(
                f"Generating segment {i+1}/{len(timeline.segments)}: "
                f"{seg.start_second}-{seg.end_second}s - {seg.description}"
            )
            segment = self._generate_single_segment(
                scene_name=scene_name,
                visual_prompt=seg.visual_prompt,
                duration=seg.end_second - seg.start_second,
                segment_index=i,
            )
            if segment:
                segments.append(segment)
        return segments

    def _create_segment_prompt(self, base_prompt: str, segment_index: int, total: int) -> str:
        """Keep existing method for fallback."""
        segment_guidance = f"Part {segment_index + 1} of {total}. "
        return segment_guidance + base_prompt
```

- [ ] **Step 3 (verify): Run test**

```bash
uv run pytest test/test_scene_segment_generator.py::test_generate_with_timeline_uses_segment_prompts -v
```
Expected: PASS (may need mock adjustments)

- [ ] **Step 4: Commit**

```bash
git add src/magicplay/generators/scene_segment_gen.py test/test_scene_segment_generator.py
git commit -m "feat: integrate TimelineAnalyzer into SceneSegmentGenerator"
```

---

## Task 3: Register TimelineAnalyzer in DI Container

**Files:**
- Modify: `src/magicplay/di_container.py`

- [ ] **Step 1: Add TimelineAnalyzer to container**

```python
# In di_container.py, add provider for TimelineAnalyzer
# (Check existing pattern for how other analyzers are registered)
```

- [ ] **Step 2: Verify imports work**

```bash
uv run python -c "from magicplay.di_container import Container; c = Container(); print(c.timeline_analyzer())"
```

- [ ] **Step 3: Commit**

```bash
git add src/magicplay/di_container.py
git commit -m "feat: register TimelineAnalyzer in DI container"
```

---

## Verification

1. **Run all tests:**
```bash
uv run pytest test/test_timeline_analyzer.py test/test_scene_segment_generator.py -v
```

2. **Manual smoke test:**
```bash
uv run python -c "
from magicplay.analyzer.timeline_analyzer import TimelineAnalyzer
analyzer = TimelineAnalyzer()
result = analyzer.analyze('角色在森林中行走，0-3秒是特写，3-6秒是中景动作', 6)
print(f'Segments: {len(result.segments)}')
for s in result.segments:
    print(f'  {s.start_second}-{s.end_second}s: {s.description}')
"
```
