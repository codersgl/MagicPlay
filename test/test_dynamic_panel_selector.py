import pytest

from magicplay.generators.dynamic_panel_selector import DynamicPanelSelector, PanelInfo


def test_dynamic_panel_selector_init():
    """Test DynamicPanelSelector can be initialized."""
    selector = DynamicPanelSelector()
    assert selector.name == "dynamic_panel_selector"
    assert selector.max_panels == 4


def test_dynamic_panel_selector_with_custom_max_panels():
    """Test DynamicPanelSelector with custom max_panels."""
    selector = DynamicPanelSelector(max_panels=6)
    assert selector.max_panels == 6


def test_panel_info_structure():
    """Test PanelInfo dataclass structure."""
    info = PanelInfo(
        panel_number=1,
        description="Close-up of Character A's angry face",
        dialogue="You took it!",
        composition="close-up",
        emotion="angry",
    )
    assert info.panel_number == 1
    assert info.description == "Close-up of Character A's angry face"
    assert info.dialogue == "You took it!"
    assert info.composition == "close-up"
    assert info.emotion == "angry"


def test_panel_info_defaults():
    """Test PanelInfo default values."""
    info = PanelInfo(panel_number=1, description="Test panel")
    assert info.dialogue is None
    assert info.composition == "wide"
    assert info.emotion == "neutral"
