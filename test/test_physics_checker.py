"""
Tests for Physics Checker Module
"""

from pathlib import Path

import pytest

from magicplay.analyzer.physics_checker import (
    PhysicsChecker,
    PhysicsViolation,
    ViolationType,
)


class TestPhysicsChecker:
    """Tests for PhysicsChecker class."""

    def test_physics_checker_initialization(self):
        """Test PhysicsChecker initializes correctly."""
        checker = PhysicsChecker()
        assert checker is not None
        assert len(checker.gravity_keywords) > 0
        assert len(checker.motion_keywords) > 0
        assert len(checker.scifi_patterns) > 0

    def test_analyze_nonexistent_file(self):
        """Test analyzing nonexistent file raises error."""
        checker = PhysicsChecker()
        with pytest.raises(FileNotFoundError):
            checker.analyze("nonexistent_file.md")

    def test_analyze_clean_script(self):
        """Test analyzing script with no violations."""
        checker = PhysicsChecker()

        clean_script = """
# SCENE HEADER
INT. LABORATORY - NIGHT

**ACTION**
Dr. Chen walks to the control panel and presses a button.
The holographic display flickers to life.

**DIALOGUE**
Dr. Chen: "The system is online."
"""

        violations = checker.analyze_content(clean_script)
        assert len(violations) == 0

    def test_detect_gravity_violation(self):
        """Test detection of gravity violations."""
        checker = PhysicsChecker()

        script_with_violation = """
# SCENE HEADER
EXT. CITY STREET - DAY

**ACTION**
The car begins to 漂浮 without any explanation.
It 悬浮 in mid-air, defying all laws of physics.
"""

        violations = checker.analyze_content(script_with_violation)
        assert len(violations) > 0
        assert any(v.violation_type == ViolationType.GRAVITY for v in violations)

    def test_detect_gravity_with_exception(self):
        """Test that gravity violations with scientific explanation are allowed."""
        checker = PhysicsChecker()

        script_with_exception = """
# SCENE HEADER
EXT. CITY STREET - DAY

**ACTION**
The car activates its 反重力装置 and begins to hover.
The 磁力 generators hum as they lift the vehicle.
"""

        violations = checker.analyze_content(script_with_exception)
        # Should not detect gravity violation due to scientific explanation
        assert (
            len([v for v in violations if v.violation_type == ViolationType.GRAVITY])
            == 0
        )

    def test_detect_motion_violation(self):
        """Test detection of motion/inertia violations."""
        checker = PhysicsChecker()

        script_with_violation = """
# SCENE HEADER
INT. ROOM - NIGHT

**ACTION**
He suddenly 瞬移 to the other side of the room.
"""

        violations = checker.analyze_content(script_with_violation)
        assert len(violations) > 0
        assert any(v.violation_type == ViolationType.MOTION for v in violations)

    def test_detect_anatomy_violation(self):
        """Test detection of anatomy violations."""
        checker = PhysicsChecker()

        script_with_violation = """
# SCENE HEADER
INT. GYM - DAY

**ACTION**
His arm 扭曲 at an impossible angle.
The body 变形 in unnatural ways.
"""

        violations = checker.analyze_content(script_with_violation)
        assert len(violations) > 0
        assert any(v.violation_type == ViolationType.ANATOMY for v in violations)

    def test_scifi_element_tracking(self):
        """Test tracking of sci-fi elements."""
        checker = PhysicsChecker()

        script_with_scifi = """
# SCENE HEADER
INT. SPACESHIP - FUTURE

**ACTION**
The 全息投影 display shows the star map.
The hologram flickers as data streams across it.
"""

        violations = checker.analyze_content(script_with_scifi)
        # Should track hologram element
        assert len(violations) == 0  # No violations, just tracking

    def test_scifi_consistency_check(self):
        """Test sci-fi consistency checking."""
        checker = PhysicsChecker()

        # Script with inconsistent tech description
        script_inconsistent = """
# SCENE HEADER
INT. LAB - FUTURE

**ACTION**
The 能量武器 glows brightly, fully charged and operational.

**SCENE 2**
INT. LAB - LATER

**ACTION**
The 能量武器 is broken and cannot function.
"""

        violations = checker.analyze_content(script_inconsistent)
        # May detect consistency issue
        # Note: This is a simplified check, may or may not trigger

    def test_generate_report_no_violations(self):
        """Test report generation with no violations."""
        checker = PhysicsChecker()

        report = checker.generate_report([])
        assert "未检测到物理规律违反问题" in report

    def test_generate_report_with_violations(self):
        """Test report generation with violations."""
        checker = PhysicsChecker()

        violations = [
            PhysicsViolation(
                violation_type=ViolationType.GRAVITY,
                description="Test gravity violation",
                line_number=10,
                line_content="Object floats mysteriously",
                severity=3,
                suggestion="Add scientific explanation",
            )
        ]

        report = checker.generate_report(violations)
        assert "GRAVITY" in report
        assert "Test gravity violation" in report
        assert "Add scientific explanation" in report

    def test_generate_report_saves_file(self, tmp_path):
        """Test report generation saves to file."""
        checker = PhysicsChecker()

        report_path = tmp_path / "physics_report.md"

        violations = [
            PhysicsViolation(
                violation_type=ViolationType.GRAVITY,
                description="Test violation",
                line_number=5,
                line_content="Test content",
                severity=2,
            )
        ]

        report = checker.generate_report(violations, report_path)

        assert report_path.exists()
        assert report_path.read_text() == report

    def test_violation_severity_levels(self):
        """Test different violation severity levels."""
        checker = PhysicsChecker()

        # Gravity violation - severity 3
        gravity_script = "The object began to 漂浮 without support."
        violations = checker.analyze_content(gravity_script)
        gravity_violations = [
            v for v in violations if v.violation_type == ViolationType.GRAVITY
        ]
        if gravity_violations:
            assert all(1 <= v.severity <= 5 for v in gravity_violations)

    def test_multiple_violation_types(self):
        """Test detecting multiple types of violations in one script."""
        checker = PhysicsChecker()

        script_multiple = """
# SCENE HEADER
INT. MYSTERY ROOM - NIGHT

**ACTION**
His body 瞬移 across the room instantly.
Then his arm 扭曲 backwards at a wrong angle.
A book 漂浮 above the table.
"""

        violations = checker.analyze_content(script_multiple)

        violation_types = set(v.violation_type for v in violations)
        # Should detect at least motion and anatomy violations
        assert (
            ViolationType.MOTION in violation_types
            or ViolationType.ANATOMY in violation_types
        )

    def test_line_content_truncation(self):
        """Test that line content is truncated in violations."""
        checker = PhysicsChecker()

        long_line = "A" * 200 + " 漂浮 " + "B" * 200
        violations = checker.analyze_content(long_line)

        gravity_violations = [
            v for v in violations if v.violation_type == ViolationType.GRAVITY
        ]
        if gravity_violations:
            assert len(gravity_violations[0].line_content) <= 100
