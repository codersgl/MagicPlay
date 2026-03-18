import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class CharacterAnchor:
    """Character consistency anchor with visual attributes."""

    name: str
    visual_tags: List[str]  # e.g., ["black_hair", "blue_eyes", "scar_on_cheek"]
    appearance: Dict[str, str]  # Detailed appearance descriptors
    personality_traits: List[str]
    relationships: Dict[str, str]  # Relationship to other characters
    image_path: Optional[str] = None  # Path to character image

    def to_prompt(self) -> str:
        """Convert to prompt string for visual generation."""
        tags = ", ".join(self.visual_tags)
        appearance_str = ", ".join([f"{k}: {v}" for k, v in self.appearance.items()])
        return f"{self.name} ({tags}) - {appearance_str}"

    def set_image_path(self, image_path: str) -> None:
        """Set the path to the character image."""
        self.image_path = image_path

    def get_image_path(self) -> Optional[str]:
        """Get the path to the character image."""
        return self.image_path


@dataclass
class VisualStyle:
    """Visual style guidelines for consistency."""

    color_palette: List[str]
    lighting_style: str
    cinematic_style: str  # e.g., "live-action", "realistic", "cinematic"
    mood: str
    key_visual_elements: List[str]


@dataclass
class StoryState:
    """Current state of the story for consistency."""

    timeline: str
    location: str
    character_states: Dict[str, Dict[str, Any]]  # Character name -> state dict
    plot_points: List[str]
    unresolved_conflicts: List[str]


class StoryConsistencyManager:
    """
    Manages story consistency across scenes and episodes.
    """

    def __init__(self, story_name: str):
        self.story_name = story_name
        self.characters: Dict[str, CharacterAnchor] = {}
        self.visual_style: Optional[VisualStyle] = None
        self.story_state = StoryState(
            timeline="Beginning",
            location="",
            character_states={},
            plot_points=[],
            unresolved_conflicts=[],
        )
        self.memory_bank: List[str] = []  # Key story moments

    def load_from_story_bible(self, bible_content: str) -> None:
        """
        Load consistency information from story bible.

        Expected format from gen_story.md:
        - Character Profiles section
        - Cinematic Style Guide section
        - World Building section
        """
        # Parse character profiles
        character_section = self._extract_section(bible_content, "Character Profiles")
        if character_section:
            self._parse_characters(character_section)

        # Parse visual style
        style_section = self._extract_section(bible_content, "Cinematic Style Guide")
        if style_section:
            self._parse_visual_style(style_section)

        # Parse world building
        world_section = self._extract_section(bible_content, "World Building")
        if world_section:
            self._parse_world_building(world_section)

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a section from markdown content."""
        # 尝试多种模式以匹配不同的markdown格式
        patterns = [
            rf"###\s*{re.escape(section_name)}.*?\n(.*?)(?:###\s|\Z)",  # 模式1：### 后可能有空格
            rf"###\s*{re.escape(section_name)}.*?\n(.*?)(?:###|\Z)",    # 模式2：没有空格
            rf"###.*?{re.escape(section_name)}.*?\n(.*?)(?:###|\Z)",    # 模式3：模糊匹配
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if extracted:  # 确保不是空字符串
                    return extracted
        
        return None

    def _parse_characters(self, character_section: str) -> None:
        """Parse character profiles from story bible."""
        lines = character_section.split("\n")
        current_character = None
        current_data = {}

        # Known property names that should NOT be treated as character names
        known_properties = {
            "身份", "人设类型", "性格特征", "ai演员锚点", "appearance",
            "身份", "人设类型", "性格特征", "ai演员锚点", "appearance"
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a character name line (not a property line)
            is_character = False
            character_name = None
            
            # Check all patterns for character names
            patterns = [
                (r"\*\s+\*\*([^(]+?)\s*(?:\([^)]+\))?\*\*\s*:", "Pattern 1: *   **角色名 (描述)**: or *   **角色名**:"),
                (r"\*\s*\*\*([^(]+?)\s*(?:\([^)]+\))?\*\*\s*:", "Pattern 2: * **角色名 (描述)**: or * **角色名**:"),
                (r"\*\*\[?([^\]\*]+)\]?\*\*", "Pattern 3: **[角色名]**"),
                (r"\*\s*\[?([^\]\:]+)\]?\s*:", "Pattern 4: * [角色名]:"),
                (r"###\s*\[?([^\]\*]+)\]?", "Pattern 5: ### [角色名]"),
                (r"\[?([^\]\:]+)\]?\s*:", "Pattern 6: [角色名]:"),
            ]
            
            for pattern, _ in patterns:
                match = re.match(pattern, line)
                if match:
                    potential_name = match.group(1).strip()
                    
                    # Skip if this is a known property
                    if potential_name.lower() in known_properties:
                        # This is a property line, not a character name
                        break
                    
                    # Additional checks: character names should not contain certain keywords
                    # and should not be too short or too long (typical Chinese names are 2-4 characters)
                    if len(potential_name) >= 2 and len(potential_name) <= 6:
                        # Common character name patterns (Chinese names, English names)
                        if re.match(r"^[\u4e00-\u9fff]{2,4}$", potential_name):  # Chinese characters
                            is_character = True
                            character_name = potential_name
                            break
                        elif re.match(r"^[A-Za-z\s]{2,20}$", potential_name):  # English names
                            is_character = True
                            character_name = potential_name
                            break
            
            if is_character and character_name:
                # Save previous character if exists
                if current_character and current_data:
                    self._create_character_anchor(current_character, current_data)

                # Start new character
                current_character = character_name
                current_data = {}
                # print(f"DEBUG: Found character: {current_character}")
            elif ":" in line and current_character:
                # Parse key-value pairs
                # 处理中文冒号和英文冒号
                # 尝试用英文冒号分割
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key, value = parts
                        # 清理键名中的markdown标记和项目符号
                        key = key.strip()
                        # 移除项目符号和粗体标记
                        key = re.sub(r"^\*\s*", "", key)  # 移除开头的*和空格
                        key = re.sub(r"\*\*", "", key)    # 移除粗体标记
                        key = key.strip().lower()
                        
                        value = value.strip()
                        # 清理markdown格式
                        value = re.sub(r"\*\*", "", value)  # 移除粗体标记
                        # 移除多余的空白
                        value = re.sub(r"\s+", " ", value)
                        current_data[key] = value
                        # print(f"DEBUG: Added data for {current_character}: {key} = {value}")
            elif current_character and line.startswith("* "):
                # Handle bullet points with key-value format
                bullet_content = line[2:].strip()
                # 处理中文冒号或英文冒号
                if ":" in bullet_content:
                    parts = bullet_content.split(":", 1)
                    if len(parts) == 2:
                        key, value = parts
                        # 清理键名中的markdown标记
                        key = key.strip()
                        key = re.sub(r"\*\*", "", key)    # 移除粗体标记
                        key = key.strip().lower()
                        
                        value = value.strip()
                        # 清理markdown格式
                        value = re.sub(r"\*\*", "", value)  # 移除粗体标记
                        # 移除多余的空白
                        value = re.sub(r"\s+", " ", value)
                        current_data[key] = value
                        # print(f"DEBUG: Added bullet data for {current_character}: {key} = {value}")

        # Save last character
        if current_character and current_data:
            self._create_character_anchor(current_character, current_data)
            # print(f"DEBUG: Created anchor for {current_character}")

    def _create_character_anchor(self, name: str, data: Dict[str, str]) -> None:
        """Create character anchor from parsed data."""
        # 清理数据键名，移除可能的markdown残留
        cleaned_data = {}
        for key, value in data.items():
            # 清理键名：移除项目符号、粗体标记和多余空格
            cleaned_key = key.strip()
            cleaned_key = re.sub(r"^\*\s*", "", cleaned_key)  # 移除开头的*和空格
            cleaned_key = re.sub(r"\*\*", "", cleaned_key)    # 移除粗体标记
            cleaned_key = cleaned_key.strip().lower()
            cleaned_data[cleaned_key] = value
        
        # Extract visual tags from appearance description
        # 尝试多种可能的键名
        appearance_keys = ["ai演员锚点", "ai演员锚点：", "appearance", "ai演员"]
        appearance_text = ""
        for key in appearance_keys:
            if key in cleaned_data:
                appearance_text = cleaned_data[key]
                break
        
        if not appearance_text:
            # 如果没有找到标准键名，尝试查找包含"锚点"的键
            for key, value in cleaned_data.items():
                if "锚点" in key or "appearance" in key.lower():
                    appearance_text = value
                    break
        
        visual_tags = self._extract_visual_tags(appearance_text)

        # Detailed appearance descriptors
        appearance = {
            "hair": self._extract_feature(appearance_text, ["hair", "发"]),
            "eyes": self._extract_feature(appearance_text, ["eyes", "眼"]),
            "clothing": self._extract_feature(
                appearance_text, ["clothing", "服装", "wear"]
            ),
            "special_features": self._extract_feature(
                appearance_text, ["scar", "疤痕", "tattoo", "纹身"]
            ),
        }

        # Personality traits
        personality_text = ""
        personality_keys = ["性格特征", "性格特征：", "personality", "性格"]
        for key in personality_keys:
            if key in cleaned_data:
                personality_text = cleaned_data[key]
                break
        
        if not personality_text:
            # 如果没有找到标准键名，尝试查找包含"性格"的键
            for key, value in cleaned_data.items():
                if "性格" in key or "personality" in key.lower():
                    personality_text = value
                    break
        
        personality = personality_text.split(",") if personality_text else []

        character = CharacterAnchor(
            name=name,
            visual_tags=visual_tags,
            appearance=appearance,
            personality_traits=personality,
            relationships={},
        )

        self.characters[name] = character

    def _extract_visual_tags(self, text: str) -> List[str]:
        """Extract visual tags from appearance description."""
        tags = []
        # Common visual features in Chinese/English
        patterns = [
            # Chinese hair features
            r"黑色及腰长发",
            r"发尾微卷",
            r"栗色长卷发",
            r"银灰色短发",
            r"背头发型",
            r"黑长直",
            r"金发",
            r"银发",
            r"卷发",
            r"长发",
            r"短发",
            # Eye features
            r"浅褐色瞳孔",
            r"清冷疏离的浅褐色瞳孔",
            r"黑色眼眸",
            r"深邃的黑色眼眸",
            r"狗狗眼",
            r"无辜的狗狗眼",
            r"蓝眼",
            r"绿眼",
            r"红唇",
            # Facial features
            r"泪痣",
            r"左眼角极淡泪痣",
            r"泪痣",
            # Clothing and accessories
            r"香槟色露肩长礼服",
            r"米白色西装套装",
            r"简约银色尾戒",
            r"银色尾戒",
            r"深色西装",
            r"蓝宝石袖扣",
            r"金丝边眼镜",
            r"白色蕾丝连衣裙",
            r"钻石手链",
            r"细钻石手链",
            r"浮夸logo",
            r"深紫色丝绒西装",
            r"西装",
            r"礼服",
            r"皮夹克",
            r"suit",
            r"dress",
            r"jacket",
            # Other features
            r"疤痕",
            r"纹身",
            r"scar",
            r"tattoo",
            # English equivalents
            r"black_hair",
            r"blonde",
            r"blue_eyes",
            r"red_lips",
        ]

        # Extract all matching patterns
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                tags.append(pattern)

        # Also extract common descriptive phrases
        descriptive_phrases = [
            r"及腰长发",
            r"长卷发",
            r"短发",
            r"瞳孔",
            r"眼眸",
            r"尾戒",
            r"手链",
            r"袖扣",
            r"眼镜",
            r"露肩",
            r"蕾丝",
            r"丝绒",
        ]
        
        for phrase in descriptive_phrases:
            if re.search(phrase, text) and phrase not in tags:
                tags.append(phrase)

        return tags

    def _extract_feature(self, text: str, keywords: List[str]) -> str:
        """Extract specific feature from text."""
        # First try to find explicit feature descriptions with colons
        for keyword in keywords:
            # Try Chinese and English colons
            for colon in ["：", ":"]:
                pattern = rf"{re.escape(keyword)}{colon}\s*(.*?)(?:[;；,，。\n]|$)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        # If no explicit feature found, look for feature in the text
        best_match = ""
        best_match_length = 0
        
        for keyword in keywords:
            # Look for keyword in text (case-insensitive)
            keyword_pattern = re.escape(keyword)
            matches = list(re.finditer(keyword_pattern, text, re.IGNORECASE))
            
            for match in matches:
                # Extract context around the keyword (up to 50 characters)
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                # Try to extract descriptive phrase after the keyword
                after_keyword = text[match.end():]
                # Look for descriptive words (Chinese characters, adjectives, etc.)
                descriptive_match = re.search(r"([\u4e00-\u9fff]+(?:\s*[\u4e00-\u9fff]+)*)", after_keyword)
                if descriptive_match:
                    description = descriptive_match.group(1).strip()
                    if len(description) > best_match_length:
                        best_match = description
                        best_match_length = len(description)
        
        return best_match if best_match else ""

    def _parse_visual_style(self, style_section: str) -> None:
        """Parse visual style from story bible."""
        lines = style_section.split("\n")
        style_data = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                style_data[key] = value

        # Create visual style object
        color_palette = (
            style_data.get("色彩基调", "").split(",")
            if "色彩基调" in style_data
            else []
        )
        lighting = style_data.get("光影氛围", "natural")
        cinematic = style_data.get("场景风格", "cinematic")
        mood = style_data.get("情感基调", "neutral")

        self.visual_style = VisualStyle(
            color_palette=color_palette,
            lighting_style=lighting,
            cinematic_style=cinematic,
            mood=mood,
            key_visual_elements=[],
        )

    def _parse_world_building(self, world_section: str) -> None:
        """Parse world building information."""
        # Extract location information
        if "Setting" in world_section:
            setting_match = re.search(r"Setting:\s*(.*)", world_section, re.IGNORECASE)
            if setting_match:
                self.story_state.location = setting_match.group(1).strip()

    def update_story_state(self, scene_content: str) -> None:
        """
        Update story state based on new scene content.

        Args:
            scene_content: Content of the latest scene
        """
        # Extract key information from scene
        self._extract_key_events(scene_content)

        # Update character states
        self._update_character_states(scene_content)

        # Update timeline and location
        self._update_timeline_location(scene_content)

        # Add to memory bank
        self._add_to_memory_bank(scene_content)

    def _extract_key_events(self, scene_content: str) -> None:
        """Extract key plot points from scene."""
        # Simple heuristic: look for significant action or dialogue
        lines = scene_content.split("\n")
        for line in lines:
            if "**ACTION**" in line or "ACTION" in line.upper():
                # Look for significant actions
                action_text = line.replace("**ACTION**", "").strip()
                if len(action_text) > 20:  # Significant action description
                    self.story_state.plot_points.append(action_text)

    def _update_character_states(self, scene_content: str) -> None:
        """Update character emotional/physical states."""
        # This is a simplified version - in reality would use NLP
        for char_name in self.characters:
            if char_name in scene_content:
                # Update character's presence and state
                if char_name not in self.story_state.character_states:
                    self.story_state.character_states[char_name] = {}

                # Simple emotional state detection
                emotional_keywords = {
                    "angry": ["愤怒", "生气", "怒吼", "angry", "furious"],
                    "happy": ["开心", "微笑", "高兴", "happy", "smile"],
                    "sad": ["悲伤", "哭泣", "难过", "sad", "cry"],
                    "afraid": ["害怕", "恐惧", "颤抖", "afraid", "fear"],
                }

                for emotion, keywords in emotional_keywords.items():
                    for keyword in keywords:
                        if keyword in scene_content and char_name in scene_content:
                            self.story_state.character_states[char_name][
                                "emotion"
                            ] = emotion
                            break

    def _update_timeline_location(self, scene_content: str) -> None:
        """Update timeline and location from scene."""
        # Extract scene header
        scene_header_match = re.search(
            r"###.*?SCENE HEADER.*?\n(.*?)\n###",
            scene_content,
            re.DOTALL | re.IGNORECASE,
        )
        if scene_header_match:
            header = scene_header_match.group(1)
            # Extract location from header (e.g., INT. LOCATION - TIME)
            location_match = re.search(
                r"(?:INT\.|EXT\.)\s+(.*?)(?:-|$)", header, re.IGNORECASE
            )
            if location_match:
                self.story_state.location = location_match.group(1).strip()

    def _add_to_memory_bank(self, scene_content: str) -> None:
        """Add key information to memory bank."""
        # Extract first 100 characters as summary (simplified)
        summary = (
            scene_content[:100] + "..." if len(scene_content) > 100 else scene_content
        )
        self.memory_bank.append(summary)

        # Keep only recent memories (last 5 scenes)
        if len(self.memory_bank) > 5:
            self.memory_bank = self.memory_bank[-5:]

    def get_consistency_prompt(self) -> str:
        """Generate consistency prompt for next scene generation."""
        prompt_parts = []

        # Character consistency
        if self.characters:
            prompt_parts.append("## Character Consistency:")
            for char in self.characters.values():
                prompt_parts.append(f"- {char.to_prompt()}")

        # Visual style consistency
        if self.visual_style:
            prompt_parts.append("\n## Visual Style:")
            prompt_parts.append(
                f"- Color Palette: {', '.join(self.visual_style.color_palette)}"
            )
            prompt_parts.append(f"- Lighting: {self.visual_style.lighting_style}")
            prompt_parts.append(f"- Style: {self.visual_style.cinematic_style}")
            prompt_parts.append(f"- Mood: {self.visual_style.mood}")

        # Story state
        prompt_parts.append("\n## Current Story State:")
        prompt_parts.append(f"- Timeline: {self.story_state.timeline}")
        prompt_parts.append(f"- Location: {self.story_state.location}")

        if self.story_state.plot_points:
            prompt_parts.append(f"- Recent Plot: {self.story_state.plot_points[-1]}")

        # Character states
        if self.story_state.character_states:
            prompt_parts.append("- Character States:")
            for char, state in self.story_state.character_states.items():
                emotion = state.get("emotion", "neutral")
                prompt_parts.append(f"  - {char}: {emotion}")

        # Memory bank
        if self.memory_bank:
            prompt_parts.append(f"\n## Recent Story Memory:")
            for i, memory in enumerate(self.memory_bank[-3:], 1):
                prompt_parts.append(f"{i}. {memory}")

        return "\n".join(prompt_parts)

    def get_character_visual_anchor(self, character_name: str) -> Optional[str]:
        """Get visual anchor prompt for specific character."""
        if character_name in self.characters:
            char = self.characters[character_name]
            return f"{char.name} must have: {', '.join(char.visual_tags)}"
        return None

    def get_formatted_visual_tags(self, character_name: str) -> Optional[str]:
        """
        Get formatted Visual Tags string for script generation.
        Returns a properly formatted string for character first appearance.

        Format: `角色名 [Visual Tags: 发型/瞳色/面部特征/服装/配饰]`

        Example: `苏晚晚 [Visual Tags: 黑长直柔顺发型，琥珀色瞳孔，左眼角浅褐色泪痣，银灰色科技风衣，极简银链项链]`
        """
        if character_name not in self.characters:
            return None

        char = self.characters[character_name]

        # Build visual tags list from appearance data
        visual_elements = []

        # Hair
        if char.appearance.get("hair"):
            visual_elements.append(char.appearance["hair"])

        # Eyes
        if char.appearance.get("eyes"):
            visual_elements.append(char.appearance["eyes"])

        # Special features (scars, tattoos, etc.)
        if char.appearance.get("special_features"):
            visual_elements.append(char.appearance["special_features"])

        # Clothing
        if char.appearance.get("clothing"):
            visual_elements.append(char.appearance["clothing"])

        # If no detailed appearance data, use raw visual tags
        if not visual_elements and char.visual_tags:
            visual_elements = char.visual_tags

        if not visual_elements:
            return None

        return f"{char.name} [Visual Tags: {', '.join(visual_elements)}]"

    def get_all_formatted_visual_tags(self) -> Dict[str, str]:
        """
        Get formatted Visual Tags for all characters.
        Returns a dictionary mapping character names to their formatted Visual Tags.
        """
        result = {}
        for name in self.characters.keys():
            formatted = self.get_formatted_visual_tags(name)
            if formatted:
                result[name] = formatted
        return result

    def get_character_image_path(self, character_name: str) -> Optional[str]:
        """Get the image path for a specific character."""
        if character_name in self.characters:
            char = self.characters[character_name]
            return char.get_image_path()
        return None

    def set_character_image_path(self, character_name: str, image_path: str) -> None:
        """Set the image path for a specific character."""
        if character_name in self.characters:
            char = self.characters[character_name]
            char.set_image_path(image_path)

    def get_all_character_images(self) -> Dict[str, str]:
        """Get all character image paths."""
        images = {}
        for name, char in self.characters.items():
            image_path = char.get_image_path()
            if image_path:
                images[name] = image_path
        return images

    def has_character_images(self) -> bool:
        """Check if all characters have image paths set."""
        if not self.characters:
            return True  # No characters means nothing to check
        
        has_images_count = 0
        for char in self.characters.values():
            if char.get_image_path():
                has_images_count += 1
        
        # Return True if at least some characters have images
        # This allows partial generation and avoids blocking all generation
        return has_images_count > 0

    def load_character_images_from_dir(self, images_dir: Path) -> Dict[str, str]:
        """
        Load character images from a directory and associate them with characters.
        Returns a dictionary mapping character names to image paths.
        """
        results = {}

        if not images_dir.exists():
            return results

        # Look for image files
        image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
        for file_path in images_dir.iterdir():
            if file_path.suffix.lower() in image_extensions:
                # Extract character name from filename (remove extension and safe name conversion)
                character_name = file_path.stem.replace("_", " ")
                results[character_name] = str(file_path)

                # Try to match with existing characters
                for name in self.characters.keys():
                    if (
                        character_name.lower() == name.lower()
                        or character_name.replace("_", " ").lower() == name.lower()
                    ):
                        self.set_character_image_path(name, str(file_path))
                        break

        return results

    def save_state(self, output_path: str) -> None:
        """Save consistency state to file."""
        import json
        from dataclasses import asdict

        state = {
            "characters": {
                name: asdict(char) for name, char in self.characters.items()
            },
            "visual_style": asdict(self.visual_style) if self.visual_style else None,
            "story_state": asdict(self.story_state),
            "memory_bank": self.memory_bank,
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self, input_path: str) -> None:
        """Load consistency state from file."""
        import json

        if Path(input_path).exists():
            with open(input_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Reconstruct objects
            self.characters = {}
            for name, char_data in state.get("characters", {}).items():
                self.characters[name] = CharacterAnchor(**char_data)

            if state.get("visual_style"):
                self.visual_style = VisualStyle(**state["visual_style"])

            self.story_state = StoryState(**state.get("story_state", {}))
            self.memory_bank = state.get("memory_bank", [])
