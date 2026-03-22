"""
MagicPlay Streamlit Frontend

A polished web UI for MagicPlay AI video generation.
Run with: uv run streamlit run src/magicplay/app.py
"""

import streamlit as st
from pathlib import Path

from magicplay.core.orchestrator import Orchestrator
from magicplay.config import get_settings
from magicplay.logging_config import setup_logging
from magicplay.utils.paths import DataManager

# Initialize logging
settings = get_settings()
setup_logging(
    level=settings.log_level,
    log_file=settings.log_file,
)


# Custom CSS for enhanced aesthetics
st.markdown("""
<style>
    /* Import distinctive fonts */
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Cormorant+Garamond:wght@400;600&display=swap');

    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0f0f1a 100%);
    }

    /* Custom title styling */
    h1 {
        font-family: 'Cormorant Garamond', serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        color: #f0f0f5 !important;
        text-shadow: 0 0 40px rgba(99, 102, 241, 0.3) !important;
    }

    /* Headers */
    h2, h3, h4, h5, h6 {
        font-family: 'Cormorant Garamond', serif !important;
        color: #e0e0e8 !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #12121a 0%, #1a1a28 100%) !important;
        border-right: 1px solid rgba(99, 102, 241, 0.2) !important;
    }

    /* Cards and containers */
    .stExpander {
        background: rgba(30, 30, 45, 0.6) !important;
        border: 1px solid rgba(99, 102, 241, 0.15) !important;
        border-radius: 12px !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(99, 102, 241, 0.5) !important;
    }

    /* Selectbox and inputs */
    .stSelectbox > div > div, .stTextInput > div > div {
        background: rgba(30, 30, 45, 0.8) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 8px !important;
    }

    /* Slider */
    .stSlider > div > div > div {
        background: rgba(99, 102, 241, 0.3) !important;
    }

    /* Tabs */
    [data-testid="stTab"] {
        background: transparent !important;
        border-bottom: 2px solid rgba(99, 102, 241, 0.3) !important;
    }

    [data-testid="stTab"]:hover {
        border-bottom-color: rgba(99, 102, 241, 0.6) !important;
    }

    [data-testid="stTab"][aria-selected="true"] {
        border-bottom-color: #6366f1 !important;
    }

    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #6366f1, #8b5cf6, #a78bfa) !important;
    }

    /* Success/Info/Warning/Error boxes */
    .stAlert {
        border-radius: 10px !important;
    }

    /* Video container styling */
    video {
        border-radius: 12px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
    }

    /* Image styling */
    img {
        border-radius: 8px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
    }

    /* Divider */
    hr {
        border-color: rgba(99, 102, 241, 0.2) !important;
    }

    /* Caption text */
    .stCaption {
        color: rgba(200, 200, 210, 0.7) !important;
    }

    /* Code blocks */
    code {
        background: rgba(30, 30, 45, 0.8) !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }

    /* Markdown content */
    .stMarkdown {
        line-height: 1.7 !important;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(20, 20, 30, 0.5);
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(99, 102, 241, 0.4);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(99, 102, 241, 0.6);
    }

    /* Spinner animation */
    .stSpinner > div {
        border-color: #6366f1 !important;
    }
</style>
""", unsafe_allow_html=True)


# Page config
st.set_page_config(
    page_title="MagicPlay - AI Video Generation",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Genre options with icons
GENRE_OPTIONS = [
    ("", "Select genre..."),
    ("Xuanhuan (玄幻)", "⚔️ Xuanhuan"),
    ("Xiuxian (修仙)", "🧘 Xiuxian"),
    ("Sci-Fi (科幻)", "🚀 Sci-Fi"),
    ("Romance (言情)", "💕 Romance"),
    ("Fantasy (奇幻)", "🔮 Fantasy"),
    ("Adventure (冒险)", "🗺️ Adventure"),
    ("Drama (剧情)", "🎭 Drama"),
]


def get_existing_stories():
    """Get list of existing stories."""
    stories = DataManager.get_stories()
    return [s.name for s in stories]


def get_existing_episodes(story_name):
    """Get list of episodes for a story."""
    episodes = DataManager.get_episodes(story_name)
    return [e.name for e in episodes]


def get_story_bible(story_name):
    """Read story bible content."""
    story_path = DataManager.get_story_path(story_name)
    bible_path = story_path / "story_bible.md"
    if bible_path.exists():
        return bible_path.read_text(encoding="utf-8")
    return None


def get_character_anchors(story_name):
    """Get character anchor images."""
    anchors_path = DataManager.get_character_anchors_path(story_name)
    if anchors_path.exists():
        return list(anchors_path.glob("*.png")) + list(anchors_path.glob("*.jpg"))
    return []


def get_scene_concepts(story_name, episode_name):
    """Get scene concept images."""
    concepts_path = DataManager.get_scene_concepts_path(story_name, episode_name)
    if concepts_path.exists():
        images = list(concepts_path.glob("*.png")) + list(concepts_path.glob("*.jpg"))
        return [img for img in images if "segment" not in img.name]
    return []


def get_videos(story_name, episode_name):
    """Get generated videos."""
    videos_path = DataManager.get_video_output_path(story_name, episode_name)
    if videos_path.exists():
        return list(videos_path.glob("*.mp4"))
    return []


def get_final_video(story_name, episode_name):
    """Get the final stitched video."""
    videos_path = DataManager.get_video_output_path(story_name, episode_name)
    if videos_path.exists():
        full_videos = list(videos_path.glob(f"{episode_name}*.mp4"))
        all_videos = list(videos_path.glob("*.mp4"))
        if full_videos:
            return full_videos[0]
        elif all_videos:
            return all_videos[0]
    return None


def delete_file(file_path):
    """Delete a file if it exists."""
    path = Path(file_path)
    if path.exists():
        path.unlink()
        return True
    return False


def get_scripts(story_name, episode_name):
    """Get generated script files."""
    scripts_path = DataManager.get_generated_scripts_path(story_name, episode_name)
    if scripts_path.exists():
        return list(scripts_path.glob("*.md"))
    return []


# Initialize session state
if "story_name" not in st.session_state:
    st.session_state.story_name = ""
if "episode_name" not in st.session_state:
    st.session_state.episode_name = ""
if "generation_complete" not in st.session_state:
    st.session_state.generation_complete = False


# Main header
st.markdown("<h1>🎬 MagicPlay</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: rgba(200,200,210,0.7); font-size: 1.1em;'>AI-Powered Video Story Generation</p>", unsafe_allow_html=True)

st.divider()


# Sidebar: Configuration
with st.sidebar:
    st.markdown("### ⚙️ Configuration", unsafe_allow_html=True)

    # Story selection
    existing_stories = get_existing_stories()
    story_options = ["[Create New Story]"] + existing_stories

    selected_story = st.selectbox(
        "Story",
        options=story_options,
        index=0 if not st.session_state.story_name else
              (story_options.index(st.session_state.story_name)
               if st.session_state.story_name in story_options else 0),
    )

    if selected_story == "[Create New Story]":
        new_story_name = st.text_input("New Story Name", placeholder="MyStory")
        if new_story_name:
            st.session_state.story_name = new_story_name
    else:
        st.session_state.story_name = selected_story

    # Episode selection
    if st.session_state.story_name:
        existing_episodes = get_existing_episodes(st.session_state.story_name)
        episode_options = ["[Create New Episode]"] + existing_episodes if existing_episodes else ["[Create New Episode]"]

        selected_episode = st.selectbox(
            "Episode",
            options=episode_options,
            index=0 if not st.session_state.episode_name else
                  (episode_options.index(st.session_state.episode_name)
                   if st.session_state.episode_name in episode_options else 0),
        )

        if selected_episode == "[Create New Episode]":
            new_episode_name = st.text_input(
                "New Episode Name",
                placeholder="S01",
                value="S01",
            )
            if new_episode_name:
                st.session_state.episode_name = new_episode_name
        else:
            st.session_state.episode_name = selected_episode

    st.divider()

    # Generation parameters
    st.markdown("### 🎛️ Generation Parameters", unsafe_allow_html=True)

    # Genre dropdown with labels
    genre_labels = [g[1] for g in GENRE_OPTIONS]
    genre_values = [g[0] for g in GENRE_OPTIONS]
    selected_label = st.selectbox("Genre", options=genre_labels, index=0)
    genre = genre_values[genre_labels.index(selected_label)] if selected_label else ""

    reference_story = st.text_input(
        "Reference Story",
        placeholder="e.g., Sword of Coming",
        help="A story to use as style reference",
    )

    max_scenes = st.slider("Number of Scenes", min_value=1, max_value=20, value=5)

    st.divider()

    # Settings display
    st.markdown("#### ℹ️ Current Settings", unsafe_allow_html=True)
    settings = get_settings()

    settings_info = f"""
    <div style='font-size: 0.85em; color: rgba(200,200,210,0.7);'>
    <p>📹 Video: <code>{settings.default_video_provider}</code></p>
    <p>🖼️ Image: <code>{settings.default_image_provider}</code></p>
    <p>⏱️ Duration: {settings.default_video_duration}s</p>
    </div>
    """
    st.markdown(settings_info, unsafe_allow_html=True)


# Main content area
if not st.session_state.story_name:
    st.info("👈 Select or create a story from the sidebar to begin.")
    st.stop()

if not st.session_state.episode_name:
    st.info("👈 Select or create an episode to continue.")
    st.stop()


# Story/Episode header
header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.markdown(f"### 📖 {st.session_state.story_name} / {st.session_state.episode_name}", unsafe_allow_html=True)

    # Show story bible preview
    bible = get_story_bible(st.session_state.story_name)
    if bible:
        with st.expander("📜 View Story Bible"):
            st.markdown(bible[:1500] + "..." if len(bible) > 1500 else bible)

with header_col2:
    st.markdown("#### 🎬 Actions", unsafe_allow_html=True)

    if st.button("Generate Episode", type="primary", use_container_width=True):
        with st.spinner(f"Generating {st.session_state.episode_name}..."):
            try:
                orchestrator = Orchestrator(
                    story_name=st.session_state.story_name,
                    episode_name=st.session_state.episode_name,
                    max_scenes=max_scenes,
                    genre=genre,
                    reference_story=reference_story,
                )

                progress_bar = st.progress(0)
                status_text = st.empty()

                final_video, _ = orchestrator.run()

                progress_bar.progress(100)
                st.session_state.generation_complete = True

                if final_video and final_video.exists():
                    st.success(f"✅ Episode generated!")
                else:
                    st.warning("Generation completed. Check outputs below.")

            except Exception as e:
                st.error(f"❌ Generation failed: {str(e)}")

    if st.button("Generate All Episodes", use_container_width=True):
        st.info("Use CLI: `uv run scripts/run.py --story ... --run-all`")


st.divider()


# Display outputs
has_content = (
    st.session_state.generation_complete or
    get_videos(st.session_state.story_name, st.session_state.episode_name)
)

if has_content:
    st.markdown("### 📁 Generated Content", unsafe_allow_html=True)

    tabs = st.tabs(["🎭 Characters", "🖼️ Concepts", "🎥 Videos", "📝 Scripts"])

    # Character anchors
    with tabs[0]:
        anchors = get_character_anchors(st.session_state.story_name)
        if anchors:
            cols = st.columns(min(len(anchors), 4))
            for i, anchor in enumerate(anchors):
                with cols[i % 4]:
                    st.image(str(anchor), caption=anchor.stem, use_container_width=True)
                    if st.button("🗑️", key=f"del_char_{i}", help=f"Delete {anchor.name}"):
                        if delete_file(anchor):
                            st.success(f"Deleted {anchor.name}")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete {anchor.name}")
        else:
            st.info("No character anchors yet. Run generation to create them.")

    # Scene concepts
    with tabs[1]:
        concepts = get_scene_concepts(st.session_state.story_name, st.session_state.episode_name)
        if concepts:
            cols = st.columns(min(len(concepts), 3))
            for i, concept in enumerate(concepts):
                with cols[i % 3]:
                    st.image(str(concept), caption=concept.stem, use_container_width=True)
                    if st.button("🗑️", key=f"del_concept_{i}", help=f"Delete {concept.name}"):
                        if delete_file(concept):
                            st.success(f"Deleted {concept.name}")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete {concept.name}")
        else:
            st.info("No scene concepts yet. Run generation to create them.")

    # Videos
    with tabs[2]:
        final_video = get_final_video(st.session_state.story_name, st.session_state.episode_name)
        if final_video and final_video.exists():
            st.video(str(final_video))
            col1, col2 = st.columns([4, 1])
            with col1:
                st.caption(f"📁 {final_video}")
            with col2:
                if st.button("🗑️ Delete", key=f"del_video_final", help="Delete this video"):
                    if delete_file(final_video):
                        st.success("Video deleted!")
                        st.rerun()
                    else:
                        st.error("Failed to delete video")
        else:
            videos = get_videos(st.session_state.story_name, st.session_state.episode_name)
            if videos:
                for i, video in enumerate(videos):
                    st.video(str(video))
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.caption(f"📁 {video}")
                    with col2:
                        if st.button("🗑️", key=f"del_vid_{i}", help=f"Delete {video.name}"):
                            if delete_file(video):
                                st.success(f"Deleted {video.name}")
                                st.rerun()
                            else:
                                st.error(f"Failed to delete {video.name}")
            else:
                st.info("No videos yet. Run generation to create them.")

    # Scripts
    with tabs[3]:
        scripts = get_scripts(st.session_state.story_name, st.session_state.episode_name)
        if scripts:
            for i, script in enumerate(sorted(scripts)):
                col1, col2 = st.columns([4, 1])
                with col1:
                    with st.expander(f"📝 {script.stem}"):
                        content = script.read_text(encoding="utf-8")
                        st.markdown(content)
                with col2:
                    st.write("")
                    if st.button("🗑️ Delete", key=f"del_script_{i}", help=f"Delete {script.name}"):
                        if delete_file(script):
                            st.success(f"Deleted {script.name}")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete {script.name}")
        else:
            st.info("No scripts yet.")

else:
    st.info("🎬 Click 'Generate Episode' to start creating content.")


# Footer
st.divider()
footer_col1, footer_col2 = st.columns([1, 3])
with footer_col1:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

with footer_col2:
    st.caption("MagicPlay v0.1.0 • AI Video Generation")
