"""
Physics Checker Module

Detects physics violations and science-fiction consistency issues in scripts.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union


class ViolationType(Enum):
    """Types of physics violations."""

    GRAVITY = "gravity"  # Objects floating, falling speed issues
    LIGHTING = "lighting"  # Inconsistent shadows, missing light sources
    MOTION = "motion"  # Teleportation, inertia violations
    MATERIAL = "material"  # Unrealistic material properties
    SCI_FI_CONSISTENCY = "sci_fi_consistency"  # Tech inconsistency within script
    ANATOMY = "anatomy"  # Impossible body movements


@dataclass
class PhysicsViolation:
    """Represents a detected physics violation."""

    violation_type: ViolationType
    description: str
    line_number: int
    line_content: str
    severity: int  # 1-5, 5 being most severe
    suggestion: str = ""


@dataclass
class SciFiElement:
    """Represents a science-fiction element in the script."""

    name: str
    description: str
    first_appearance_line: int
    rules: List[str] = field(default_factory=list)  # Rules/limitations of this tech
    occurrences: List[Tuple[int, str]] = field(default_factory=list)


class PhysicsChecker:
    """
    Checks scripts for physics violations and sci-fi consistency.

    Features:
    - Detect gravity violations (floating objects, impossible falls)
    - Check lighting consistency (shadows, light sources)
    - Verify motion physics (teleportation, inertia)
    - Validate anatomy (impossible body movements)
    - Track sci-fi elements for internal consistency
    """

    def __init__(self):
        # Gravity violation keywords
        self.gravity_keywords = [
            "漂浮", "浮空", "悬浮", "飘浮", "float", "levitat", "hover",
            "无故漂浮", "凭空漂浮", "违背重力",
        ]

        # Motion violation keywords
        self.motion_keywords = [
            "瞬移", "瞬间移动", "凭空出现", "突然消失",
            "teleport", "suddenly appear", "suddenly disappear",
            "违背惯性", "违反惯性", "impossible turn",
        ]

        # Anatomy violation keywords
        self.anatomy_keywords = [
            "扭曲", "变形", "twisted", "contorted", "impossible angle",
            "关节反转", "身体扭曲", " unnatural bend",
        ]

        # Lighting keywords
        self.lighting_keywords = [
            "阴影方向", "光源", "shadow direction", "light source",
            "无影", "multiple shadows", "inconsistent lighting",
        ]

        # Sci-fi element patterns
        self.scifi_patterns = {
            "hologram": [r"全息投影", r"全息", r"hologram", r"holo"],
            "ai_interface": [r"智能界面", r"AI 界面", r"virtual interface"],
            "future_vehicle": [r"飞行器", r"悬浮车", r"flying car", r"hover vehicle"],
            "energy_weapon": [r"能量武器", r"激光", r"energy weapon", r"blaster"],
            "neural_implant": [r"神经植入", r"脑机接口", r"neural implant"],
        }

        # Physics exception rules (things that ARE allowed in sci-fi context)
        self.allowed_exceptions = [
            r"反重力装置",  # Anti-gravity device explicitly mentioned
            r"推进器",  # Thrusters explaining movement
            r"磁力",  # Magnetic forces
            r"力场",  # Force fields
        ]

    def analyze(self, script_path: Union[str, Path]) -> List[PhysicsViolation]:
        """
        Analyze a script file for physics violations.

        Args:
            script_path: Path to the script file

        Returns:
            List of detected physics violations
        """
        script_path = Path(script_path)
        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")

        content = script_path.read_text(encoding="utf-8")
        return self.analyze_content(content)

    def analyze_content(self, content: str) -> List[PhysicsViolation]:
        """
        Analyze script content for physics violations.

        Args:
            content: Script content as string

        Returns:
            List of detected physics violations
        """
        violations = []
        lines = content.split("\n")

        # Track sci-fi elements for consistency checking
        scifi_elements: Dict[str, SciFiElement] = {}

        for line_num, line in enumerate(lines, 1):
            # Check for gravity violations
            gravity_violation = self._check_gravity(line, line_num)
            if gravity_violation:
                violations.append(gravity_violation)

            # Check for motion violations
            motion_violation = self._check_motion(line, line_num)
            if motion_violation:
                violations.append(motion_violation)

            # Check for anatomy violations
            anatomy_violation = self._check_anatomy(line, line_num)
            if anatomy_violation:
                violations.append(anatomy_violation)

            # Track sci-fi elements
            self._track_scifi_element(line, line_num, scifi_elements)

        # Check sci-fi consistency
        consistency_violations = self._check_scifi_consistency(scifi_elements)
        violations.extend(consistency_violations)

        return violations

    def _check_gravity(self, line: str, line_num: int) -> Optional[PhysicsViolation]:
        """Check for gravity violations."""
        line_lower = line.lower()

        # Check if line contains gravity-related keywords
        for keyword in self.gravity_keywords:
            if keyword.lower() in line_lower:
                # Check if it's an allowed exception
                is_allowed = any(
                    re.search(pattern, line) for pattern in self.allowed_exceptions
                )

                if not is_allowed:
                    return PhysicsViolation(
                        violation_type=ViolationType.GRAVITY,
                        description=f"Potential gravity violation detected: '{keyword}' found",
                        line_number=line_num,
                        line_content=line.strip()[:100],
                        severity=3,
                        suggestion="考虑添加科学解释（如反重力装置、磁力等）或修改为符合物理规律的描述",
                    )

        return None

    def _check_motion(self, line: str, line_num: int) -> Optional[PhysicsViolation]:
        """Check for motion/inertia violations."""
        line_lower = line.lower()

        for keyword in self.motion_keywords:
            if keyword.lower() in line_lower:
                # Check if it's an allowed exception (e.g., established sci-fi tech)
                is_allowed = any(
                    re.search(pattern, line) for pattern in self.allowed_exceptions
                )

                if not is_allowed:
                    return PhysicsViolation(
                        violation_type=ViolationType.MOTION,
                        description=f"Potential motion physics violation: '{keyword}' found",
                        line_number=line_num,
                        line_content=line.strip()[:100],
                        severity=4,
                        suggestion="添加动作过渡描述，或提供科学解释（如瞬移装置）",
                    )

        return None

    def _check_anatomy(self, line: str, line_num: int) -> Optional[PhysicsViolation]:
        """Check for anatomy violations."""
        line_lower = line.lower()

        for keyword in self.anatomy_keywords:
            if keyword.lower() in line_lower:
                return PhysicsViolation(
                    violation_type=ViolationType.ANATOMY,
                    description=f"Potential anatomy violation: '{keyword}' found",
                    line_number=line_num,
                    line_content=line.strip()[:100],
                    severity=3,
                    suggestion="修改为符合人体解剖学的动作描述",
                )

        return None

    def _track_scifi_element(
        self, line: str, line_num: int, elements: Dict[str, SciFiElement]
    ) -> None:
        """Track science-fiction elements for consistency checking."""
        line_lower = line.lower()

        for element_type, patterns in self.scifi_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    if element_type not in elements:
                        # First occurrence - create new element
                        elements[element_type] = SciFiElement(
                            name=element_type,
                            description=line.strip()[:200],
                            first_appearance_line=line_num,
                        )
                    else:
                        # Record this occurrence
                        elements[element_type].occurrences.append(
                            (line_num, line.strip()[:100])
                        )
                    break

    def _check_scifi_consistency(
        self, elements: Dict[str, SciFiElement]
    ) -> List[PhysicsViolation]:
        """Check for sci-fi element consistency across the script."""
        violations = []

        for element_type, element in elements.items():
            # Check if the element is described differently in different places
            if len(element.occurrences) > 1:
                # Analyze descriptions for contradictions
                descriptions = [desc for _, desc in element.occurrences]

                # Simple heuristic: check for contradictory keywords
                positive_terms = ["强大", "有效", "working", "active", "功能正常"]
                negative_terms = ["失效", "损坏", "broken", "malfunction", "无法使用"]

                has_positive = any(
                    any(term in desc.lower() for term in positive_terms)
                    for desc in descriptions
                )
                has_negative = any(
                    any(term in desc.lower() for term in negative_terms)
                    for desc in descriptions
                )

                if has_positive and has_negative:
                    # Check if there's an explanation for the change
                    # (this is a simplified check)
                    violations.append(
                        PhysicsViolation(
                            violation_type=ViolationType.SCI_FI_CONSISTENCY,
                            description=f"Sci-fi element '{element_type}' may have inconsistent descriptions",
                            line_number=element.first_appearance_line,
                            line_content=element.description[:100],
                            severity=2,
                            suggestion=f"确保'{element_type}'的设定在全剧中保持一致，如有变化需提供合理解释",
                        )
                    )

        return violations

    def generate_report(
        self, violations: List[PhysicsViolation], output_path: Optional[Path] = None
    ) -> str:
        """
        Generate a human-readable report of physics violations.

        Args:
            violations: List of detected violations
            output_path: Optional path to save the report

        Returns:
            Report string
        """
        if not violations:
            report = "✅ 未检测到物理规律违反问题！"
        else:
            report = f"⚠️ 检测到 {len(violations)} 个潜在问题\n\n"

            # Group by type
            by_type: Dict[ViolationType, List[PhysicsViolation]] = {}
            for v in violations:
                if v.violation_type not in by_type:
                    by_type[v.violation_type] = []
                by_type[v.violation_type].append(v)

            for vtype, vlist in by_type.items():
                report += f"\n## {vtype.value.upper()} ({len(vlist)} issues)\n\n"
                for v in vlist:
                    report += f"### 行 {v.line_number} (严重程度：{'⭐' * v.severity})\n"
                    report += f"> {v.line_content}\n\n"
                    report += f"**问题**: {v.description}\n\n"
                    if v.suggestion:
                        report += f"**建议**: {v.suggestion}\n\n"
                    report += "---\n\n"

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            print(f"Physics check report saved to: {output_path}")

        return report
from typing import Union
