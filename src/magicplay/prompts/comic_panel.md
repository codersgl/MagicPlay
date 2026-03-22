# Comic Panel Generation Prompt

You are a professional manga/comic artist generating a comic panel.

## Scene Context
- Story: {story_name}
- Episode: {episode_name}
- Scene: {scene_name}
- Scene Script: {scene_script}

## Characters in Scene
{character_descriptions}

## Panel Description
{panel_description}

## Dialogue/Text (if any)
{dialogue}

## Style Requirements
Style: {comic_style}
- For anime style: anime art, cel shaded, vibrant colors, detailed linework
- For comic style: realistic proportions, bold colors, halftone dots
- For webtoon style: clean lines, expressive faces, vertical format
- For ink style: black and white, brush strokes, traditional manga feel

## Generation Instructions
1. Create a high-quality comic panel image matching the description
2. Include any dialogue/text naturally integrated into the panel
3. Maintain character consistency with the provided character descriptions
4. Use appropriate composition for the panel type (establishing shot, close-up, action, etc.)
5. Output only the image - no additional text or annotations

## Negative Prompt
low quality, blurry, distorted, deformed, bad anatomy, extra fingers, watermark, text overlay