#!/usr/bin/env python3
"""
Test script to verify ScriptAnalyzer functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from magicplay.analyzer.script_analyzer import ScriptAnalyzer


def test_analyzer():
    """Test the ScriptAnalyzer with sample scripts."""
    analyzer = ScriptAnalyzer(min_duration=5, max_duration=30)

    # Test with a dialogue-heavy script
    dialogue_script = """
### SCENE HEADER
INT. COFFEE SHOP - DAY

### VISUAL KEY
Coffee shop interior, warm lighting, two characters sitting at a table.

### SCRIPT BODY

**ACTION**
The coffee shop is quiet, with soft jazz playing in the background.

JOHN
(sipping coffee)
So, what do you think about the new proposal?

MARY
(looking thoughtful)
I'm not sure. It seems risky to invest that much upfront.

**ACTION**
John leans forward, his expression serious.

JOHN
But think about the potential return. We could triple our investment within a year.

MARY
(shaking head)
Or lose everything. Remember what happened with the last venture?
    """

    print("Testing dialogue-heavy script:")
    result = analyzer.analyze(dialogue_script)
    print(f"  Scene Type: {result.scene_type.value}")
    print(f"  Total Words: {result.total_words}")
    print(f"  Dialogue Lines: {result.dialogue_lines}")
    print(f"  Action Density: {result.action_density:.2f}")
    print(f"  Estimated Duration: {result.estimated_duration}s")
    print(f"  Complexity Score: {result.complexity_score:.2f}")
    print()

    # Test with an action-heavy script
    action_script = """
### SCENE HEADER
EXT. CITY STREETS - NIGHT

### VISUAL KEY
Rain-slicked streets, neon signs reflecting in puddles, fast-paced chase sequence.

### SCRIPT BODY

**ACTION**
The car screeches around the corner, tires smoking. Rain pelts the windshield as the wipers struggle to keep up.

**ACTION**
A motorcycle emerges from an alley, cutting off the car's path. The rider wears black leather, face obscured by a helmet.

**ACTION**
The car swerves, narrowly avoiding a collision. It mounts the sidewalk, scattering trash cans and cardboard boxes.

**ACTION**
Inside the car, the driver grips the wheel tightly, knuckles white. The passenger looks back, eyes wide with fear.

**ACTION**
The motorcycle accelerates, pulling alongside the car. The rider reaches into a jacket pocket.

**ACTION**
A flash of metal - a gun! The rider aims at the car's tires.

**ACTION**
BANG! BANG! Two shots ring out. Sparks fly as bullets ricochet off the pavement.

**ACTION**
The car lurches violently, hitting a fire hydrant. Water geysers into the air, creating a temporary curtain.
    """

    print("Testing action-heavy script:")
    result = analyzer.analyze(action_script)
    print(f"  Scene Type: {result.scene_type.value}")
    print(f"  Total Words: {result.total_words}")
    print(f"  Dialogue Lines: {result.dialogue_lines}")
    print(f"  Action Density: {result.action_density:.2f}")
    print(f"  Estimated Duration: {result.estimated_duration}s")
    print(f"  Complexity Score: {result.complexity_score:.2f}")
    print()

    # Test with a mixed script
    mixed_script = """
### SCENE HEADER
INT. LABORATORY - NIGHT

### VISUAL KEY
High-tech lab with holographic displays, glowing equipment, tense atmosphere.

### SCRIPT BODY

**ACTION**
DR. ELARA stands before a massive console, fingers flying across holographic keys. Data streams cascade around her.

DR. ELARA
(muttering to herself)
Come on, stabilize... just a little longer...

**ACTION**
A warning light flashes red. An alarm begins to blare.

ASSISTANT
(rushing in)
Doctor! The containment field is collapsing!

**ACTION**
Elara doesn't look up, her focus absolute on the console.

DR. ELARA
I know! I'm trying to reinforce it!

**ACTION**
She slams her palm on a large red button. The entire lab shakes. Equipment rattles on shelves.

**ACTION**
Outside the reinforced window, the containment field flickers violently. Blue energy arcs across its surface.

ASSISTANT
(cowering)
It's not working!

DR. ELARA
(through gritted teeth)
It has to work! I won't lose another one!
    """

    print("Testing mixed script:")
    result = analyzer.analyze(mixed_script)
    print(f"  Scene Type: {result.scene_type.value}")
    print(f"  Total Words: {result.total_words}")
    print(f"  Dialogue Lines: {result.dialogue_lines}")
    print(f"  Action Density: {result.action_density:.2f}")
    print(f"  Estimated Duration: {result.estimated_duration}s")
    print(f"  Complexity Score: {result.complexity_score:.2f}")
    print()

    # Test with an existing script file
    existing_scripts = list(
        Path("data/story/MyStory/01_EpisodeOne/generated_scripts").glob("*.md")
    )
    if existing_scripts:
        print("Testing with existing script file:")
        script_path = existing_scripts[0]
        result = analyzer.analyze_file(str(script_path))
        if result:
            print(f"  File: {script_path.name}")
            print(f"  Scene Type: {result.scene_type.value}")
            print(f"  Total Words: {result.total_words}")
            print(f"  Dialogue Lines: {result.dialogue_lines}")
            print(f"  Action Density: {result.action_density:.2f}")
            print(f"  Estimated Duration: {result.estimated_duration}s")
            print(f"  Complexity Score: {result.complexity_score:.2f}")
            print(f"  Character Count: {result.character_count}")
            print(f"  Location Changes: {result.location_changes}")

    print("\n✅ ScriptAnalyzer test completed successfully!")


if __name__ == "__main__":
    test_analyzer()
